"""Admin deal management — create/adjust/deactivate flash sales. catalog.* permission surface
(deals ride the catalog like coupons); every mutation activity-logged.

No per-object policy, so (like category/vendor/coupon/banner) this converts to ``api_resource`` +
a declared ``Authorize`` per action rather than ``authorize_resource`` (K5/DR-0056).
"""

from typing import Any

from arvel import abort
from arvel.activitylog import activity
from arvel.auth.middleware import Authorize
from arvel.dates import Date
from arvel.http import Request
from arvel.routing import Controller, ControllerMiddleware
from arvel.support import current_user
from arvel.validation import ValidationException

from app.controllers.serializers import iso as _iso
from app.enums import Permission
from app.models.deal import Deal
from app.models.product import Product
from app.models.user import User
from app.schemas import AdminDealOut, DealIn, DealUpdateIn
from app.services import deal_service


def _current_user() -> User:
    user: User | None = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    return user


def _validate_percent(percent_off: int) -> None:
    if not (1 <= percent_off <= 90):
        raise ValidationException({"percent_off": ["A deal must be 1–90 percent off."]})


def _parse_when(value: str, field: str) -> Any:
    try:
        return Date.parse(value)
    except Exception:
        raise ValidationException({field: ["Not a valid ISO-8601 datetime."]}) from None


async def _out(deal: Deal) -> AdminDealOut:
    product = await Product.in_locale().where("id", deal.product_id).first()
    return AdminDealOut(
        id=deal.id,
        product_id=deal.product_id,
        product_name=product.translation.name if product is not None else "?",
        percent_off=deal.percent_off,
        starts_at=_iso(deal.starts_at),
        ends_at=_iso(deal.ends_at),
        active=bool(deal.active),
        live=deal_service.is_live(deal),
    )


class DealController(Controller):
    """Deal CRUD — index/store/update/destroy, all through this class's normal
    ``Router.resource()`` wiring (``update`` used to be pulled out explicitly — see
    ``CategoryController``'s docstring for why that's no longer needed, DR-0057)."""

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
            ControllerMiddleware(
                Authorize(Permission.CATALOG_DELETE.value), only=("destroy",)
            ),
        ]

    async def index(self, request: Request) -> list[AdminDealOut]:
        return [await _out(d) for d in await Deal.order_by("id", "desc").get()]

    async def store(self, request: Request, data: DealIn) -> AdminDealOut:
        user = _current_user()
        _validate_percent(data.percent_off)
        if await Product.find(data.product_id) is None:
            raise ValidationException({"product_id": ["Unknown product."]})
        starts = _parse_when(data.starts_at, "starts_at")
        ends = _parse_when(data.ends_at, "ends_at")
        if ends <= starts:
            raise ValidationException(
                {"ends_at": ["The deal must end after it starts."]}
            )
        deal = await Deal.create(
            product_id=data.product_id,
            percent_off=data.percent_off,
            starts_at=starts,
            ends_at=ends,
            active=data.active,
        )
        await (
            activity()
            .caused_by(user)
            .performed_on(deal)
            .with_properties(
                {"percent_off": data.percent_off, "product_id": data.product_id}
            )
            .log("created deal")
        )
        return await _out(deal)

    async def update(
        self, request: Request, deal: Deal, data: DealUpdateIn
    ) -> AdminDealOut:
        # catalog.update is enforced by this controller's Authorize middleware (DR-0055), so a
        # denied caller 403s uniformly whether or not the id exists.
        user = _current_user()
        if data.percent_off is not None:
            _validate_percent(data.percent_off)
            deal.percent_off = data.percent_off
        if data.starts_at is not None:
            deal.starts_at = _parse_when(data.starts_at, "starts_at")
        if data.ends_at is not None:
            deal.ends_at = _parse_when(data.ends_at, "ends_at")
        if data.active is not None:
            deal.active = data.active
        await deal.save()
        await (
            activity()
            .caused_by(user)
            .performed_on(deal)
            .with_properties({"active": bool(deal.active)})
            .log("updated deal")
        )
        return await _out(deal)

    async def destroy(self, request: Request, deal: Deal) -> dict[str, str]:
        # catalog.delete is enforced by the controller's Authorize middleware (DR-0055/K5).
        user = _current_user()
        await deal.delete()
        await activity().caused_by(user).performed_on(deal).log("deleted deal")
        return {"status": "deleted"}
