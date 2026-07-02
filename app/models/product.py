"""The Product model — a catalog item, with variants, a category, and an image gallery.

Product images use arvel's **media library** (``HasMedia``): images attach to the ``images``
collection and each upload generates ``thumb`` + ``preview`` conversions automatically.
"""

from typing import Any, ClassVar, TypedDict

from arvel import Model
from arvel.database import SoftDeletes
from arvel.localization import current_locale
from arvel.media import HasMedia, MediaConversion

from app.models.product_media import ProductMedia
from arvel.search import Searchable

from app.casts.translations import TranslationCast, TranslationsCast
from app.enums import ProductStatus
from app.schemas import Translate

IMAGES = "images"  # the product image gallery collection
SUPPORTED_LOCALES = {
    "en",
    "fr",
}  # storefront locales; whitelisted → no SQL injection via Accept-Language
DEFAULT_LOCALE = "en"


class TranslationDoc(TypedDict):
    locale: str
    name: str
    description: str | None


class SearchableProduct(TypedDict):
    """The typed search-index document for a product (see Product.to_searchable_array)."""

    id: int
    slug: str
    translations: list[
        TranslationDoc
    ]  # Meilisearch searches the nested per-locale name/description


class Product(HasMedia, Searchable, Model, SoftDeletes):
    __table_name__ = "products"
    __media_model__ = ProductMedia  # gallery items expose url/thumb/preview (media.md → extending Media)
    __fields__: ClassVar[dict[str, type]] = {
        "category_id": int,
        "vendor_id": int,
        "slug": str,
        "translations": dict,  # ONE locale-major jsonb: {"en": {"name","description"}, "fr": {...}}
        "price_cents": int,
        "rating_sum": int,
        "rating_count": int,
        "currency": str,
        "status": str,
        "published": bool,
    }
    __fillable__: ClassVar[list[str]] = [
        "category_id",
        "vendor_id",
        "slug",
        "translations",
        "price_cents",
        "currency",
        "status",
        "published",
    ]
    __casts__: ClassVar[dict[str, Any]] = {
        "status": ProductStatus,
        "published": bool,
        "translations": TranslationsCast(),  # full column → list[Translate] (admin)
        "translation": TranslationCast(),  # the scope_in_locale projection → Translate (storefront)
    }

    # the scalar columns the storefront fetches (NOT translations — only the active-locale `translation`)
    _LOCALE_COLUMNS = (
        "id, slug, price_cents, currency, status, category_id, vendor_id, published, "
        "rating_sum, rating_count, created_at, updated_at"
    )

    def scope_in_locale(self, query: Any, locale: str | None = None) -> Any:
        """Project ONLY the active locale's object as `translation` (Translate cast), not the whole
        translations map — `translations->'<locale>'` with a fallback to the default locale."""
        loc = locale or current_locale.get()
        if loc not in SUPPORTED_LOCALES:
            loc = DEFAULT_LOCALE
        return query.select_raw(Product._LOCALE_COLUMNS).select_raw(
            f"COALESCE(translations->'{loc}', translations->'{DEFAULT_LOCALE}') AS translation"
        )

    def register_media_conversions(self) -> list[MediaConversion]:
        """Derived versions generated for every gallery image (Spatie conversions). WebP — the modern
        web format: ~25–35% smaller than JPEG at equal quality, and it keeps alpha (no RGBA flatten).
        Universally supported by current browsers."""
        return [
            MediaConversion("thumb", width=256, height=320, fmt="WEBP"),
            MediaConversion("preview", width=600, height=750, fmt="WEBP"),
        ]

    def to_searchable_array(self) -> dict[str, Any]:
        """The search document (Searchable contract → ``dict[str, Any]``): slug + every locale's
        name/description (Meilisearch searches the nested values). Keyed by id (``get_search_key``)."""
        translations: list[Translate] = self.translations
        record: SearchableProduct = {
            "id": int(self.id),
            "slug": str(self.slug),
            "translations": [
                {"locale": t.locale, "name": t.name, "description": t.description}
                for t in translations
            ],
        }
        return dict(record)

    def category(self) -> Any:
        from app.models.category import Category

        return self.belongs_to(Category)

    def vendor(self) -> Any:
        from app.models.vendor import Vendor

        return self.belongs_to(Vendor)

    def reviews(self) -> Any:
        from app.models.review import Review

        return self.morph_many(Review, "subject")

    def variants(self) -> Any:
        from app.models.product_variant import ProductVariant

        return self.has_many(ProductVariant)

    # one correlated EXISTS against the retrievability view, used as a flag (admin) and a filter
    # (storefront) — see CatalogVisibilityService for how the view is refreshed.
    _VISIBLE = "EXISTS(SELECT 1 FROM retrievable_products rp WHERE rp.id = products.id)"

    def scope_with_visibility(self, query: Any, only_visible: bool = False) -> Any:
        """Annotate each row with ``is_visible`` (admin) and/or keep only the visible rows
        (``only_visible=True``, storefront). Same EXISTS predicate for both."""
        if only_visible:
            return query.where_raw(Product._VISIBLE)
        return query.select_raw("products.*").select_raw(
            f"{Product._VISIBLE} AS is_visible"
        )
