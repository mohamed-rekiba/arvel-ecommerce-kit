"""Product media — admin gallery upload + serving, via arvel's media library.

Admin upload attaches an image to the product's ``images`` collection (conversions auto-generated);
serving streams a media item (original or a named conversion) from its disk.
"""

from arvel import abort
from app.i18n import trans
from arvel.http import Request, Response
from arvel.kernel import app
from arvel.media import Media
from arvel.validation import ValidationException

from app.controllers.catalog_controller import gallery_image_out
from app.models.product import IMAGES, Product
from app.schemas import GalleryImageOut
from app.services.product_image_service import ProductImageService


async def upload_image(request: Request, id: Product) -> list[GalleryImageOut]:
    """Attach an uploaded image to the product gallery. catalog.update is enforced by the route's
    Authorize middleware (DR-0055) — it runs before binding, so a denied caller 403s uniformly
    whether or not the product id exists; returns the updated gallery."""
    product = id

    upload = await request.file("image")
    if upload is None:
        raise ValidationException({"image": [trans("shop.errors.image_required")]})
    raw = await upload.read()
    try:
        await ProductImageService().attach_uploaded(
            product,
            raw,
            file_name=upload.client_name or "image.png",
            mime_type=upload.content_type,
        )
    except Exception as exc:  # noqa: BLE001 — any decode/store failure is a client error
        raise ValidationException(
            {"image": [trans("shop.errors.file_not_image")]}
        ) from exc

    return [gallery_image_out(m) for m in await product.get_media(IMAGES)]


async def delete_image(request: Request, id: Product) -> list[GalleryImageOut]:
    """Remove ONE gallery image (row + stored files via HasMedia.delete_media); returns the
    updated gallery. catalog.update is enforced by the route's Authorize middleware (DR-0055);
    a foreign media id can't cross products."""
    product = id
    if not await product.delete_media(int(request.path_param("media_id"))):
        abort(404, trans("shop.errors.media_not_found"))
    return [gallery_image_out(m) for m in await product.get_media(IMAGES)]


async def serve_media(request: Request) -> Response:
    """Stream a media item — the original, or a named conversion (thumb/preview)."""
    media = await Media.find_or_fail(int(request.path_param("id")))
    conversion = request.path_param("conversion", None)
    path = media.get_path(conversion)
    if path is None:
        abort(404, trans("shop.errors.media_not_found"))
    disk = app("filesystem").disk(media.disk)
    if not await disk.exists(path):
        abort(404, trans("shop.errors.media_not_found"))
    data = await disk.get(path)
    # a conversion's type follows its stored extension (webp/jpeg/png); the original keeps its mime
    if conversion:
        ext = path.rsplit(".", 1)[-1].lower()
        content_type = {
            "webp": "image/webp",
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
        }.get(ext, "image/png")
    else:
        content_type = media.mime_type or "application/octet-stream"
    return Response(content=data, status=200, headers={"content-type": content_type})
