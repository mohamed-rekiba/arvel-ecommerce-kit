"""The Product model — a catalog item, with variants, a category, and an image gallery.

Product images use arvel's **media library** (``HasMedia``): images attach to the ``images``
collection and each upload generates ``thumb`` + ``preview`` conversions automatically.
"""

from typing import Any, ClassVar, TypedDict

from arvel import Model
from arvel.localization import HasTranslations, Translatable
from arvel.media import HasMedia, MediaConversion
from arvel.search import Searchable

from app.enums import ProductStatus

IMAGES = "images"  # the product image gallery collection


class SearchableProduct(TypedDict):
    """The typed search-index document for a product (see Product.to_searchable_array)."""

    id: int
    slug: str
    name: dict[str, str]  # {locale: value} — Meilisearch searches the nested values
    description: str | None


class Product(HasMedia, HasTranslations, Searchable, Model):
    __table_name__ = "products"
    __fields__: ClassVar[dict[str, type]] = {
        "category_id": int,
        "vendor_id": int,
        "name": dict,  # translatable JSON {locale: value} (read as a str via the Translatable cast)
        "slug": str,
        "description": str,
        "price_cents": int,
        "currency": str,
        "status": str,
        "published": bool,
    }
    __fillable__: ClassVar[list[str]] = [
        "category_id",
        "vendor_id",
        "name",
        "slug",
        "description",
        "price_cents",
        "currency",
        "status",
        "published",
    ]
    __casts__: ClassVar[dict[str, Any]] = {
        "status": ProductStatus,
        "published": bool,
        "name": Translatable(),  # per-locale {locale: value}, read as the current locale
    }

    def register_media_conversions(self) -> list[MediaConversion]:
        """Derived versions generated for every gallery image (Spatie conversions)."""
        return [
            MediaConversion("thumb", width=256, height=320, fmt="PNG"),
            MediaConversion("preview", width=600, height=750, fmt="PNG"),
        ]

    def to_searchable_array(self) -> dict[str, Any]:
        """The search document (Searchable contract → ``dict[str, Any]``): the slug, the per-locale
        ``name`` map (Meilisearch searches the nested ``name.en`` / ``name.fr`` … values), and the
        description. Keyed by id (``get_search_key``)."""
        name: dict[str, str] = self.translations("name")
        record: SearchableProduct = {
            "id": int(self.id),
            "slug": str(self.slug),
            "name": name,
            "description": self.description,
        }
        return dict(record)

    def category(self) -> Any:
        from app.models.category import Category

        return self.belongs_to(Category)

    def vendor(self) -> Any:
        from app.models.vendor import Vendor

        return self.belongs_to(Vendor)

    def variants(self) -> Any:
        from app.models.product_variant import ProductVariant

        return self.has_many(ProductVariant)
