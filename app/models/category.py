"""The Category model — catalog taxonomy (supports nesting via self-reference)."""

from typing import Any, ClassVar

from arvel import Model


class Category(Model):
    __table_name__ = "categories"
    __fields__: ClassVar[dict[str, type]] = {
        "name": str,
        "slug": str,
        "parent_id": int,
    }
    __fillable__: ClassVar[list[str]] = ["name", "slug", "parent_id"]

    def products(self) -> Any:
        from app.models.product import Product

        return self.has_many(Product)

    def parent(self) -> Any:
        return self.belongs_to(Category, foreign_key="parent_id")

    def children(self) -> Any:
        return self.has_many(Category, foreign_key="parent_id")
