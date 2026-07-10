"""Admin coupon management — create/adjust/deactivate discount codes. Uses the catalog.*
permission surface (marketing rides the catalog taxonomy); every mutation activity-logged."""

from arvel import abort
from arvel.activitylog import activity
from arvel.http import Request
from arvel.support import current_user
from arvel.validation import ValidationException

from app.enums import CouponType, Permission
from app.models.coupon import Coupon
from app.models.user import User
from app.schemas import AdminCouponOut, CouponIn, CouponUpdateIn
from app.services.coupon_service import normalize_code


def _current_user() -> User:
    user: User | None = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    return user


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


async def index(request: Request) -> list[AdminCouponOut]:
    user = _current_user()
    if not await user.can(Permission.CATALOG_VIEW.value):
        abort(403, "You lack catalog access.")
    return [_out(c) for c in await Coupon.order_by("id").get()]


async def store(request: Request, data: CouponIn) -> AdminCouponOut:
    user = _current_user()
    if not await user.can(Permission.CATALOG_CREATE.value):
        abort(403, "You lack catalog access.")
    code = normalize_code(data.code)
    if not code:
        raise ValidationException({"code": ["The code is required."]})
    if data.type is CouponType.PERCENT and not (1 <= data.value <= 100):
        raise ValidationException({"value": ["A percent coupon must be 1–100."]})
    if data.value <= 0:
        raise ValidationException({"value": ["The value must be positive."]})
    if await Coupon.where("code", code).first() is not None:
        raise ValidationException({"code": ["This code already exists."]})
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
        .with_properties({"code": code, "type": data.type.value, "value": data.value})
        .log("created coupon")
    )
    return _out(coupon)


async def update(request: Request, id: Coupon, data: CouponUpdateIn) -> AdminCouponOut:
    """Activate/deactivate or adjust limits — deactivation takes effect immediately (checkout
    re-validates every redemption). catalog.update is enforced by the route's Authorize
    middleware (DR-0055), so a denied caller 403s uniformly whether or not the id exists."""
    user = _current_user()
    coupon = id
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
