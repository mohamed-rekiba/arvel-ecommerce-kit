"""One redemption of a coupon by an order (user id or guest email drives per-customer limits)."""

from typing import Any, ClassVar

from arvel import Model


class CouponRedemption(Model):
    __table_name__ = "coupon_redemptions"
    __fields__: ClassVar[dict[str, type]] = {
        "coupon_id": int,
        "order_id": int,
        "user_id": int,
        "contact_email": str,
    }
    __fillable__: ClassVar[list[str]] = [
        "coupon_id",
        "order_id",
        "user_id",
        "contact_email",
    ]

    def coupon(self) -> Any:
        from app.models.coupon import Coupon

        return self.belongs_to(Coupon)
