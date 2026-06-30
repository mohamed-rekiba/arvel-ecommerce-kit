"""The Order model — a placed order with a lifecycle status (state machine in app.enums)."""

from typing import Any, ClassVar

from arvel import Model

from app.enums import OrderStatus


class Order(Model):
    __table_name__ = "orders"
    __fields__: ClassVar[dict[str, type]] = {
        "user_id": int,
        "status": str,
        "total_cents": int,
    }
    __fillable__: ClassVar[list[str]] = ["user_id", "status", "total_cents"]
    __casts__: ClassVar[dict[str, Any]] = {"status": OrderStatus}

    def items(self) -> Any:
        from app.models.order_item import OrderItem

        return self.has_many(OrderItem)

    def user(self) -> Any:
        from app.models.user import User

        return self.belongs_to(User)
