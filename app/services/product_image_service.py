"""Product image service — fetch + attach product gallery images via arvel's **media library**.

Used by the seeder (downloads real catalog images from a public provider through the arvel Http
client) and the admin upload controller. Images attach to the product's ``images`` media collection;
the model's registered conversions (thumb/preview) are generated automatically. Kept in the service
layer (not the controller/seeder) per the convention.
"""

import tempfile
from pathlib import Path

from anyio import open_file
from arvel import Http
from arvel.media import HasMedia, Image
from arvel.support.facades import Config, Log

from app.models.product import IMAGES


def _disk() -> str:
    """The configured default storage disk (config/filesystems.py → FILESYSTEM_DISK): `local` in
    dev/tests, `s3` for RustFS. Resolved at call time so it honours the running config, not a hardcode."""
    return str(Config.get("filesystems.default", "local"))


class ProductImageService:
    async def attach_uploaded(
        self,
        model: HasMedia,
        raw: bytes,
        *,
        file_name: str = "image.png",
        mime_type: str | None = None,
        collection: str = IMAGES,
    ) -> None:
        """Attach an admin-uploaded image to a HasMedia model's collection (products, banners —
        conversions auto-generated per the model's registrations)."""
        Image.open(
            raw
        )  # decode-validate — reject a non-image / corrupt upload before storing
        await model.add_media(
            raw, file_name=file_name, mime_type=mime_type
        ).to_media_collection(collection, disk=_disk())

    async def download_and_attach(
        self, model: HasMedia, url: str, *, file_name: str, collection: str = IMAGES
    ) -> bool:
        """Download an image from ``url`` and attach it to the gallery. The body streams straight
        to a temp file (``Http.sink()`` — constant memory regardless of image size) and is read
        back for the attach (``add_media`` is bytes-only). Returns False (a no-op) if the fetch
        fails — so seeding never crashes when offline."""
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir) / "download"
                # follow_redirects: image CDNs (Picsum, etc.) 302 to the actual file
                response = (
                    await Http.timeout(15)
                    .sink(tmp_path)
                    .get(url, follow_redirects=True)
                )
                if not response.successful():
                    return False
                async with await open_file(tmp_path, "rb") as fh:
                    data = await fh.read()
                if not data:
                    return False
                await model.add_media(
                    data,
                    file_name=file_name,
                    mime_type=response.header("content-type"),
                ).to_media_collection(collection, disk=_disk())
        except Exception as exc:  # noqa: BLE001 — offline / bad image / storage down → seed
            # without it, don't crash; but log so a real storage failure isn't silently swallowed
            Log.warning("product image fetch/attach failed", url=url, error=repr(exc))
            return False
        return True
