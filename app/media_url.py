"""One serving-URL rule for a stored media row, shared by every API projection (avatar, product,
banner, admin library) so the storefront and back office never diverge on how a file is addressed."""

from arvel.media import Media


def media_serving_url(media: Media, conversion: str | None = None) -> str:
    """The public storage/CDN URL when the disk exposes one (s3/RustFS), else the app-streamed
    /api/media proxy — never force the proxy on top of an already-public bucket URL."""
    url: str | None = media.get_url(conversion)
    if url and url.startswith(("http://", "https://")):
        return url
    suffix = f"/{conversion}" if conversion else ""
    return f"/api/media/{media.id}{suffix}"
