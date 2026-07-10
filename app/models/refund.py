"""The Refund model — a reversal of one SUCCEEDED Payment, mirrored from the payment gateway."""

from typing import Any, ClassVar

from arvel import Model

from app.enums import RefundStatus


class Refund(Model):
    __table_name__ = "refunds"
    __fields__: ClassVar[dict[str, type]] = {
        "order_id": int,
        "payment_id": int,
        "gateway_charge_id": str,
        "gateway_refund_id": str,
        "amount_cents": int,
        "status": str,
        "restock": bool,
    }
    __fillable__: ClassVar[list[str]] = [
        "order_id",
        "payment_id",
        "gateway_charge_id",
        "gateway_refund_id",
        "amount_cents",
        "status",
        "restock",
    ]
    __casts__: ClassVar[dict[str, Any]] = {"status": RefundStatus}

    def order(self) -> Any:
        from app.models.order import Order

        return self.belongs_to(Order)

    def payment(self) -> Any:
        from app.models.payment import Payment

        return self.belongs_to(Payment)
