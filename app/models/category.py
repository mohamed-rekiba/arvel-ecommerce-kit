"""The Category model — catalog taxonomy (supports nesting via self-reference)."""

from typing import Any, ClassVar

from arvel import Model
from arvel.localization import current_locale

from app.casts.translations import TranslationCast, TranslationsCast

SUPPORTED_LOCALES = {"en", "fr"}
DEFAULT_LOCALE = "en"


class Category(Model):
    __table_name__ = "categories"
    __fields__: ClassVar[dict[str, type]] = {
        "slug": str,
        "translations": dict,  # locale-major {"en": {"name"}, "fr": {...}}
        "parent_id": int,
        "published": bool,
    }
    __fillable__: ClassVar[list[str]] = ["slug", "translations", "parent_id", "published"]
    __casts__: ClassVar[dict[str, Any]] = {
        "published": bool,
        "translations": TranslationsCast(),  # full column → list[Translate] (admin)
        "translation": TranslationCast(),  # the scope_in_locale projection → Translate (storefront)
    }

    _VISIBLE = "EXISTS(SELECT 1 FROM retrievable_categories rc WHERE rc.id = categories.id)"
    _LOCALE_COLUMNS = "id, slug, parent_id, published, created_at, updated_at"

    def scope_with_visibility(self, query: Any, only_visible: bool = False) -> Any:
        """``is_visible`` flag (admin) and/or keep only visible categories (storefront)."""
        if only_visible:
            return query.where_raw(Category._VISIBLE)
        return query.select_raw("categories.*").select_raw(f"{Category._VISIBLE} AS is_visible")

    def scope_in_locale(self, query: Any, locale: str | None = None) -> Any:
        """Project only the active locale's object as `translation` (not the whole translations map)."""
        loc = locale or current_locale.get()
        if loc not in SUPPORTED_LOCALES:
            loc = DEFAULT_LOCALE
        return query.select_raw(Category._LOCALE_COLUMNS).select_raw(
            f"COALESCE(translations->'{loc}', translations->'{DEFAULT_LOCALE}') AS translation"
        )

    def products(self) -> Any:
        from app.models.product import Product

        return self.has_many(Product)

    def parent(self) -> Any:
        return self.belongs_to(Category, foreign_key="parent_id")

    def children(self) -> Any:
        return self.has_many(Category, foreign_key="parent_id")
