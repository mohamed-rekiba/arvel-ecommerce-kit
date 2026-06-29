"""The ProductVariant model — a purchasable SKU under a product (size/colour/...)."""

from typing import Any, ClassVar

from arvel import Model


class ProductVariant(Model):
    __table_name__ = "product_variants"
    __fields__: ClassVar[dict[str, type]] = {
        "product_id": int,
        "sku": str,
        "name": str,
        "price_adjustment_cents": int,
        "stock": int,
    }
    __fillable__: ClassVar[list[str]] = [
        "product_id",
        "sku",
        "name",
        "price_adjustment_cents",
        "stock",
    ]

    def product(self) -> Any:
        from app.models.product import Product

        return self.belongs_to(Product)
