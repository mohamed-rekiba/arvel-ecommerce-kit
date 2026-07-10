"""The Banner model — one hero-carousel slide: per-locale copy + a media-library image."""

from typing import Any, ClassVar

from arvel import Model
from arvel.media import HasMedia, MediaConversion

from app.casts.translations import LocaleMapCast
from app.models.media import AppMedia

HERO = "hero"  # the banner's single-image media collection


class Banner(HasMedia, Model):
    __table_name__ = "banners"
    __media_model__ = (
        AppMedia  # hero/mobile expose serving_url() (media.md → extending Media)
    )
    __fields__: ClassVar[dict[str, type]] = {
        "translations": dict,  # locale-major {"en": {"title", "subtitle", "chip", "cta_label"}}
        "cta_to": str,
        "sort": int,
        "active": bool,
    }
    __fillable__: ClassVar[list[str]] = ["translations", "cta_to", "sort", "active"]
    __casts__: ClassVar[dict[str, Any]] = {
        "translations": LocaleMapCast(),
        "active": bool,
    }

    def register_media_conversions(self) -> list[MediaConversion]:
        """Hero-sized derivatives (WEBP, like the product gallery)."""
        return [
            MediaConversion("hero", width=1600, height=700, fmt="WEBP"),
            MediaConversion("mobile", width=800, height=500, fmt="WEBP"),
        ]
