"""A customer's request to be told when a sold-out variant returns (one-shot)."""

from typing import Any, ClassVar

from arvel import Model


class StockAlert(Model):
    __table_name__ = "stock_alerts"
    __fields__: ClassVar[dict[str, type]] = {
        "product_variant_id": int,
        "user_id": int,
    }
    __fillable__: ClassVar[list[str]] = ["product_variant_id", "user_id"]

    def variant(self) -> Any:
        from app.models.product_variant import ProductVariant

        return self.belongs_to(ProductVariant)
