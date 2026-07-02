"""The Order model — a placed order with a lifecycle status (state machine in app.enums), the
customer contact + shipping address captured at checkout, and the server-computed money breakdown
(subtotal + shipping + tax = total, in an explicit currency)."""

from typing import Any, ClassVar

from arvel import Model

from app.enums import Currency, OrderStatus


class Order(Model):
    __table_name__ = "orders"
    __fields__: ClassVar[dict[str, type]] = {
        "user_id": int,
        "status": str,
        "contact_email": str,
        "ship_name": str,
        "ship_line1": str,
        "ship_line2": str,
        "ship_city": str,
        "ship_postal_code": str,
        "ship_country": str,
        "subtotal_cents": int,
        "shipping_cents": int,
        "tax_cents": int,
        "total_cents": int,
        "currency": str,
    }
    __fillable__: ClassVar[list[str]] = [
        "user_id",
        "status",
        "contact_email",
        "ship_name",
        "ship_line1",
        "ship_line2",
        "ship_city",
        "ship_postal_code",
        "ship_country",
        "subtotal_cents",
        "shipping_cents",
        "tax_cents",
        "total_cents",
        "currency",
    ]
    __casts__: ClassVar[dict[str, Any]] = {"status": OrderStatus, "currency": Currency}

    def items(self) -> Any:
        from app.models.order_item import OrderItem

        return self.has_many(OrderItem)

    def user(self) -> Any:
        from app.models.user import User

        return self.belongs_to(User)
