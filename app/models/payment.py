"""The Payment model — a charge against an order, mirrored from the payment gateway."""

from typing import Any, ClassVar

from arvel import Model

from app.enums import PaymentStatus


class Payment(Model):
    __table_name__ = "payments"
    __fields__: ClassVar[dict[str, type]] = {
        "order_id": int,
        "gateway_charge_id": str,
        "amount_cents": int,
        "status": str,
    }
    __fillable__: ClassVar[list[str]] = [
        "order_id",
        "gateway_charge_id",
        "amount_cents",
        "status",
    ]
    __casts__: ClassVar[dict[str, Any]] = {"status": PaymentStatus}

    def order(self) -> Any:
        from app.models.order import Order

        return self.belongs_to(Order)
