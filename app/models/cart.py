"""The Cart model — a shopping cart, owned by a user (persistent) or a guest (by cart token)."""

from typing import Any, ClassVar

from arvel import Model


class Cart(Model):
    __table_name__ = "carts"
    __fields__: ClassVar[dict[str, type]] = {
        "user_id": int,
        "token": str,
        "coupon_code": str,
    }
    __fillable__: ClassVar[list[str]] = ["user_id", "token", "coupon_code"]

    def items(self) -> Any:
        from app.models.cart_item import CartItem

        return self.has_many(CartItem)

    def user(self) -> Any:
        from app.models.user import User

        return self.belongs_to(User)
