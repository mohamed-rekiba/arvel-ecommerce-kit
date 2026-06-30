"""The OrderItem model — a line in a placed order (price captured at checkout time)."""

from typing import Any, ClassVar

from arvel import Model


class OrderItem(Model):
    __table_name__ = "order_items"
    __fields__: ClassVar[dict[str, type]] = {
        "order_id": int,
        "product_variant_id": int,
        "quantity": int,
        "unit_price_cents": int,
    }
    __fillable__: ClassVar[list[str]] = [
        "order_id",
        "product_variant_id",
        "quantity",
        "unit_price_cents",
    ]

    def order(self) -> Any:
        from app.models.order import Order

        return self.belongs_to(Order)

    def variant(self) -> Any:
        from app.models.product_variant import ProductVariant

        return self.belongs_to(ProductVariant)
