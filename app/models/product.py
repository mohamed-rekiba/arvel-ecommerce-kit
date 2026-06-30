"""The Product model — a catalog item, with variants, a category, and an image gallery.

Product images use arvel's **media library** (``HasMedia``): images attach to the ``images``
collection and each upload generates ``thumb`` + ``preview`` conversions automatically.
"""

from typing import Any, ClassVar

from arvel import Model
from arvel.media import HasMedia, MediaConversion

from app.enums import ProductStatus

IMAGES = "images"  # the product image gallery collection


class Product(HasMedia, Model):
    __table_name__ = "products"
    __fields__: ClassVar[dict[str, type]] = {
        "category_id": int,
        "name": str,
        "slug": str,
        "description": str,
        "price_cents": int,
        "currency": str,
        "status": str,
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

    def register_media_conversions(self) -> list[MediaConversion]:
        """Derived versions generated for every gallery image (Spatie conversions)."""
        return [
            MediaConversion("thumb", width=256, height=320, fmt="PNG"),
            MediaConversion("preview", width=600, height=750, fmt="PNG"),
        ]

    def category(self) -> Any:
        from app.models.category import Category

        return self.belongs_to(Category)

    def variants(self) -> Any:
        from app.models.product_variant import ProductVariant

        return self.has_many(ProductVariant)
