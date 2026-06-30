"""The Product model — a catalog item, with variants and a category."""

from typing import Any, ClassVar

from arvel import Model

from app.enums import ProductStatus


class Product(Model):
    __table_name__ = "products"
    __fields__: ClassVar[dict[str, type]] = {
        "category_id": int,
        "name": str,
        "slug": str,
        "description": str,
        "price_cents": int,
        "currency": str,
        "status": str,
        "image_path": str,
    }
    __fillable__: ClassVar[list[str]] = [
        "category_id",
        "name",
        "slug",
        "description",
        "price_cents",
        "currency",
        "status",
    ]
    __casts__: ClassVar[dict[str, Any]] = {"status": ProductStatus}

    def category(self) -> Any:
        from app.models.category import Category

        return self.belongs_to(Category)

    def variants(self) -> Any:
        from app.models.product_variant import ProductVariant

        return self.has_many(ProductVariant)
