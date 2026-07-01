"""Product image service — fetch + attach product gallery images via arvel's **media library**.

Used by the seeder (downloads real catalog images from a public provider through the arvel Http
client) and the admin upload controller. Images attach to the product's ``images`` media collection;
the model's registered conversions (thumb/preview) are generated automatically. Kept in the service
layer (not the controller/seeder) per the convention.
"""

from arvel import Http
from arvel.media import Image
from arvel.support.facades import Config

from app.models.product import IMAGES, Product


def _disk() -> str:
    """The configured default storage disk (config/filesystems.py → FILESYSTEM_DISK): `local` in
    dev/tests, `s3` for RustFS. Resolved at call time so it honours the running config, not a hardcode."""
    return Config.get("filesystems.default", "local")


class ProductImageService:
    async def attach_uploaded(
        self,
        product: Product,
        raw: bytes,
        *,
        file_name: str = "image.png",
        mime_type: str | None = None,
    ) -> None:
        """Attach an admin-uploaded image to the product gallery (conversions auto-generated)."""
        Image.open(
            raw
        )  # decode-validate — reject a non-image / corrupt upload before storing
        await product.add_media(
            raw, file_name=file_name, mime_type=mime_type
        ).to_media_collection(IMAGES, disk=_disk())

    async def download_and_attach(
        self, product: Product, url: str, *, file_name: str
    ) -> bool:
        """Download an image from ``url`` (arvel Http client) and attach it to the gallery. Returns
        False (a no-op) if the fetch fails — so seeding never crashes when offline."""
        try:
            # follow_redirects: image CDNs (Picsum, etc.) 302 to the actual file
            response = await Http.timeout(15).get(url, follow_redirects=True)
            if response.status_code >= 400 or not response.content:
                return False
            await product.add_media(
                response.content,
                file_name=file_name,
                mime_type=response.headers.get("content-type"),
            ).to_media_collection(IMAGES, disk=_disk())
        except Exception:  # noqa: BLE001 — offline / bad image → seed without it, don't crash
            return False
        return True
