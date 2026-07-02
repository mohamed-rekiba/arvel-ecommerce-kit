"""The storefront announcement bar — surfaces the newest LIVE coupon an admin flagged with
``announce`` (the reference's orange "coupon code" marquee). 404 when nothing is announced,
which the storefront treats as "no bar"."""

from arvel import abort
from arvel.dates import Date
from arvel.http import Request

from app.enums import CouponType
from app.models.coupon import Coupon
from app.schemas import AnnouncementOut


async def show(request: Request) -> AnnouncementOut:
    now = Date.now()
    coupons = (
        await Coupon.where("announce", True)
        .where("active", True)
        .order_by("id", "desc")
        .get()
    )
    for coupon in coupons:
        if coupon.starts_at is not None and now < coupon.starts_at:
            continue
        if coupon.ends_at is not None and now > coupon.ends_at:
            continue
        kind = (
            coupon.type
            if isinstance(coupon.type, CouponType)
            else CouponType(coupon.type)
        )
        return AnnouncementOut(code=coupon.code, type=kind, value=coupon.value)
    abort(404, "Nothing announced")
