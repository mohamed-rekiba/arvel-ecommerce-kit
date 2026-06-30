"""Product media — admin gallery upload + serving, via arvel's media library.

Admin upload attaches an image to the product's ``images`` collection (conversions auto-generated);
serving streams a media item (original or a named conversion) from its disk. Showcases the media
library (HasMedia / add_media / conversions) + the filesystem.
"""

from arvel import abort
from arvel.http import Request, Response
from arvel.kernel import app
from arvel.media import Media
from arvel.support import current_user
from arvel.validation import ValidationException

from app.controllers.catalog_controller import gallery_image_out
from app.models.product import IMAGES, Product
from app.schemas import GalleryImageOut
from app.services.product_image_service import ProductImageService


async def upload_image(request: Request) -> list[GalleryImageOut]:
    """Attach an uploaded image to the product gallery (admins only); returns the updated gallery."""
    user = current_user.get()
    if user is None or not user.is_admin():
        abort(403, "Only admins may upload product images.")
    product = await Product.find_or_fail(int(request.path_param("id")))

    upload = await request.file("image")
    if upload is None:
        raise ValidationException({"image": ["An image file is required."]})
    raw = await upload.read()
    try:
        await ProductImageService().attach_uploaded(
            product, raw, file_name=upload.client_name or "image.png", mime_type=upload.content_type
        )
    except Exception as exc:  # noqa: BLE001 — any decode/store failure is a client error
        raise ValidationException({"image": ["The file is not a valid image."]}) from exc

    return [gallery_image_out(m) for m in await product.get_media(IMAGES)]


async def serve_media(request: Request) -> Response:
    """Stream a media item — the original, or a named conversion (thumb/preview)."""
    media = await Media.find_or_fail(int(request.path_param("id")))
    conversion = request.path_param("conversion", None)
    path = media.get_path(conversion)
    if path is None:
        abort(404, "Media not found")
    disk = app("filesystem").disk(media.disk)
    if not await disk.exists(path):
        abort(404, "Media not found")
    data = await disk.get(path)
    # conversions are PNG; the original keeps its stored mime type
    content_type = "image/png" if conversion else (media.mime_type or "application/octet-stream")
    return Response(content=data, status=200, headers={"content-type": content_type})
