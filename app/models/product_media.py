"""ProductMedia — a ``Media`` subclass that exposes the gallery image URLs as attributes.

The conversion names (``thumb``/``preview``) are the app's, not the framework's, so arvel doesn't
invent accessors for them (media.md → "Extending the media model"). We add them here: ``url`` (original),
``thumb`` (256×320), ``preview`` (600×750), each backed by ``media.get_url(...)`` — which returns the
disk's configured public ``url`` base + the path. ``__appends__`` includes them in ``to_dict()``/JSON.
Product points at this via ``__media_model__``.
"""

from typing import Any

from arvel import Attribute

from app.models.media import AppMedia


class ProductMedia(AppMedia):
    __table_name__ = (
        "media"  # share the one media table (arvel builds a table per class otherwise)
    )
    __appends__ = ["url", "thumb", "preview"]  # serialize these in to_dict()/JSON

    def url(self) -> Attribute:
        def get(value: Any, attrs: dict[str, Any]) -> str:
            return self.serving_url()

        return Attribute(get=get)

    def thumb(self) -> Attribute:
        def get(value: Any, attrs: dict[str, Any]) -> str:
            return self.serving_url("thumb")

        return Attribute(get=get)

    def preview(self) -> Attribute:
        def get(value: Any, attrs: dict[str, Any]) -> str:
            return self.serving_url("preview")

        return Attribute(get=get)
