"""The Category model — catalog taxonomy (supports nesting via self-reference)."""

from typing import Any, ClassVar

from arvel import Model
from arvel.localization import HasTranslations, Translatable


class Category(HasTranslations, Model):
    __table_name__ = "categories"
    __fields__: ClassVar[dict[str, type]] = {
        "name": dict,  # translatable JSON {locale: value} (read as a str via the Translatable cast)
        "slug": str,
        "parent_id": int,
        "published": bool,
    }
    __fillable__: ClassVar[list[str]] = ["name", "slug", "parent_id", "published"]
    __casts__: ClassVar[dict[str, Any]] = {"published": bool, "name": Translatable()}

    _VISIBLE = "EXISTS(SELECT 1 FROM retrievable_categories rc WHERE rc.id = categories.id)"

    def scope_with_visibility(self, query: Any, only_visible: bool = False) -> Any:
        """``is_visible`` flag (admin) and/or keep only visible categories (storefront)."""
        if only_visible:
            return query.where_raw(Category._VISIBLE)
        return query.select_raw("categories.*").select_raw(f"{Category._VISIBLE} AS is_visible")

    def products(self) -> Any:
        from app.models.product import Product

        return self.has_many(Product)

    def parent(self) -> Any:
        return self.belongs_to(Category, foreign_key="parent_id")

    def children(self) -> Any:
        return self.has_many(Category, foreign_key="parent_id")
