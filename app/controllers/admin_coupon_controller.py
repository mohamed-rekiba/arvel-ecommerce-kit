"""Admin coupon management — create/adjust/deactivate discount codes. Uses the catalog.*
permission surface (marketing rides the catalog taxonomy); every mutation activity-logged.

No per-object policy (no per-coupon dimension to a "can create/update" check), so — like category
and vendor — this converts to ``api_resource`` + a declared ``Authorize`` per action (K5/DR-0056)
rather than ``authorize_resource``.
"""

from app.auth.require import require_user as _current_user
from app.i18n import trans
from arvel.activitylog import activity
from arvel.auth.middleware import Authorize
from arvel.http import Request
from arvel.routing import Controller, ControllerMiddleware
from arvel.validation import ValidationException

from app.enums import CouponType, Permission
from app.models.coupon import Coupon
from app.schemas import AdminCouponOut, CouponIn, CouponUpdateIn
from app.services.coupon_service import normalize_code


def _out(coupon: Coupon) -> AdminCouponOut:
    kind = (
        coupon.type if isinstance(coupon.type, CouponType) else CouponType(coupon.type)
    )
    return AdminCouponOut(
        id=coupon.id,
        code=coupon.code,
        type=kind,
        value=coupon.value,
        min_subtotal_cents=coupon.min_subtotal_cents or 0,
        usage_limit=coupon.usage_limit,
        per_customer_limit=coupon.per_customer_limit,
        uses=coupon.uses or 0,
        active=bool(coupon.active),
        announce=bool(getattr(coupon, "announce", False)),
        starts_at=None if coupon.starts_at is None else str(coupon.starts_at),
        ends_at=None if coupon.ends_at is None else str(coupon.ends_at),
    )


class CouponController(Controller):
    """Coupon CRUD — index/store/update only. There's no `destroy`: a coupon that's already been
    redeemed can't disappear from order history, so admins deactivate one via `active=False`
    instead. ``update`` registers through this class's normal ``Router.resource()`` wiring — see
    ``CategoryController``'s docstring for why it no longer needs to be pulled out."""

    @classmethod
    def middleware(cls) -> list[ControllerMiddleware]:
        return [
            ControllerMiddleware(
                Authorize(Permission.CATALOG_VIEW.value), only=("index",)
            ),
            ControllerMiddleware(
                Authorize(Permission.CATALOG_CREATE.value), only=("store",)
            ),
            ControllerMiddleware(
                Authorize(Permission.CATALOG_UPDATE.value), only=("update",)
            ),
        ]

    async def index(self, request: Request) -> list[AdminCouponOut]:
        return [_out(c) for c in await Coupon.order_by("id").get()]

    async def store(self, request: Request, data: CouponIn) -> AdminCouponOut:
        user = _current_user()
        code = normalize_code(data.code)
        if not code:
            raise ValidationException(
                {"code": [trans("shop.errors.coupon_code_required")]}
            )
        if data.type is CouponType.PERCENT and not (1 <= data.value <= 100):
            raise ValidationException(
                {"value": [trans("shop.errors.coupon_percent_range")]}
            )
        if data.value <= 0:
            raise ValidationException(
                {"value": [trans("shop.errors.value_not_positive")]}
            )
        if await Coupon.where("code", code).first() is not None:
            raise ValidationException(
                {"code": [trans("shop.errors.coupon_code_exists")]}
            )
        coupon = await Coupon.create(
            code=code,
            type=data.type,
            value=data.value,
            min_subtotal_cents=data.min_subtotal_cents,
            usage_limit=data.usage_limit,
            per_customer_limit=data.per_customer_limit,
            uses=0,
            active=True,
            announce=data.announce,
        )
        await (
            activity()
            .caused_by(user)
            .performed_on(coupon)
            .with_properties(
                {"code": code, "type": data.type.value, "value": data.value}
            )
            .log("created coupon")
        )
        return _out(coupon)

    async def update(
        self, request: Request, coupon: Coupon, data: CouponUpdateIn
    ) -> AdminCouponOut:
        """Activate/deactivate or adjust limits — deactivation takes effect immediately (checkout
        re-validates every redemption). catalog.update is enforced by this controller's Authorize
        middleware (DR-0055), so a denied caller 403s uniformly whether or not the id exists."""
        user = _current_user()
        if data.active is not None:
            coupon.active = data.active
        if data.usage_limit is not None:
            coupon.usage_limit = data.usage_limit
        if data.per_customer_limit is not None:
            coupon.per_customer_limit = data.per_customer_limit
        if data.min_subtotal_cents is not None:
            coupon.min_subtotal_cents = data.min_subtotal_cents
        if data.announce is not None:
            coupon.announce = data.announce
        await coupon.save()
        await (
            activity()
            .caused_by(user)
            .performed_on(coupon)
            .with_properties({"code": coupon.code, "active": bool(coupon.active)})
            .log("updated coupon")
        )
        return _out(coupon)
