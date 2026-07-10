"""AppMedia — the app's Media subclass (media.md → "extending the media model"). It carries the one
serving-URL rule the whole app resolves files through, so the storefront and back office never
diverge on how a stored file is addressed. HasMedia models point ``__media_model__`` here."""

from arvel.media import Media


class AppMedia(Media):
    __table_name__ = (
        "media"  # share the one media table (arvel builds a table per class otherwise)
    )

    def serving_url(self, conversion: str | None = None) -> str:
        """Where a client fetches this file: the public storage/CDN URL when the disk exposes one
        (s3/RustFS), else the app-streamed /api/media proxy — never the proxy over a public URL."""
        url = self.get_url(conversion)
        if url and url.startswith(("http://", "https://")):
            return url
        suffix = f"/{conversion}" if conversion else ""
        return f"/api/media/{self.id}{suffix}"
