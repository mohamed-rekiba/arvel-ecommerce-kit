"""WishlistItem — a product a customer has saved (user↔product pivot)."""

from typing import Any, ClassVar

from arvel import Model


class WishlistItem(Model):
    __table_name__ = "wishlist_items"
    __fields__: ClassVar[dict[str, type]] = {
        "user_id": int,
        "product_id": int,
    }
    __fillable__: ClassVar[list[str]] = ["user_id", "product_id"]

    def product(self) -> Any:
        from app.models.product import Product

        return self.belongs_to(Product)
