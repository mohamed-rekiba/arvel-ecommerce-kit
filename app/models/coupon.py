"""The Coupon model — an order-level discount code, with usage limits and an active window."""

from datetime import datetime
from typing import Any, ClassVar

from arvel import Model

from app.enums import CouponType


class Coupon(Model):
    __table_name__ = "coupons"
    __fields__: ClassVar[dict[str, type]] = {
        "code": str,
        "type": str,
        "value": int,
        "min_subtotal_cents": int,
        "starts_at": datetime,
        "ends_at": datetime,
        "usage_limit": int,
        "per_customer_limit": int,
        "uses": int,
        "active": bool,
    }
    __fillable__: ClassVar[list[str]] = [
        "code",
        "type",
        "value",
        "min_subtotal_cents",
        "starts_at",
        "ends_at",
        "usage_limit",
        "per_customer_limit",
        "uses",
        "active",
    ]
    __casts__: ClassVar[dict[str, Any]] = {
        "type": CouponType,
        "active": bool,
        "starts_at": "datetime",
        "ends_at": "datetime",
    }

    def redemptions(self) -> Any:
        from app.models.coupon_redemption import CouponRedemption

        return self.has_many(CouponRedemption)
