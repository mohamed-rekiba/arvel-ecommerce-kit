"""The CartItem model — a line in a cart: a product variant + quantity at a captured unit price."""

from typing import Any, ClassVar

from arvel import Model


class CartItem(Model):
    __table_name__ = "cart_items"
    __fields__: ClassVar[dict[str, type]] = {
        "cart_id": int,
        "product_variant_id": int,
        "quantity": int,
        "unit_price_cents": int,
    }
    __fillable__: ClassVar[list[str]] = [
        "cart_id",
        "product_variant_id",
        "quantity",
        "unit_price_cents",
    ]

    def cart(self) -> Any:
        from app.models.cart import Cart

        return self.belongs_to(Cart)

    def variant(self) -> Any:
        from app.models.product_variant import ProductVariant

        return self.belongs_to(ProductVariant)
