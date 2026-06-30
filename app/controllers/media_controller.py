"""Product media — admin image upload + serving.

Showcases arvel's media module (``arvel.media.Image``: decode → resize → encode) and filesystem
(``Storage`` / ``UploadedFile.store``). On upload the image is **decoded** (real validation, not just
a content-type header), the original is stored, and a **thumbnail variant** is generated via the
media module and stored alongside. The default disk is ``local``; FILESYSTEM_DISK=s3 → RustFS/S3.
"""

from arvel import Storage, abort
from arvel.http import Request, Response
from arvel.media import Image
from arvel.support import Str, current_user
from arvel.validation import ValidationException

from app.models.product import Product
from app.schemas import ImageOut

_THUMB_MAX = 256  # longest-edge thumbnail size
_EXT_CONTENT_TYPE = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}


def _thumbnail(image: Image) -> Image:
    """Fit the image within a _THUMB_MAX square, preserving aspect ratio (no upscaling)."""
    width, height = image.width, image.height
    longest = max(width, height)
    if longest <= _THUMB_MAX:
        return image
    scale = _THUMB_MAX / longest
    return image.resize(max(1, int(width * scale)), max(1, int(height * scale)))


async def upload_image(request: Request) -> ImageOut:
    """Store an uploaded product image + a generated thumbnail (admins only)."""
    user = current_user.get()
    if user is None or not user.is_admin():
        abort(403, "Only admins may upload product images.")
    product = await Product.find_or_fail(int(request.path_param("id")))

    upload = await request.file("image")
    if upload is None:
        raise ValidationException({"image": ["An image file is required."]})
    raw = await upload.read()
    try:
        image = Image.open(raw)  # real decode — rejects a mislabeled / corrupt upload
    except Exception as exc:  # noqa: BLE001 — any decode failure is a client error
        raise ValidationException({"image": ["The file is not a valid image."]}) from exc

    # store the original (the bytes we already read — don't re-read the consumed upload stream),
    # then generate + store a thumbnail via the media module
    name = Str.random(40)
    ext = (upload.extension or "png").lower()
    original_path = f"products/{name}.{ext}"
    await Storage.put(original_path, raw)
    thumb_path = f"products/thumbs/{name}.png"
    await Storage.put(thumb_path, _thumbnail(image).encode("PNG"))

    product.image_path = original_path
    product.image_thumb_path = thumb_path
    await product.save()
    return ImageOut(image_path=original_path, thumb_path=thumb_path)


async def _serve(path: str | None) -> Response:
    if not path or not await Storage.exists(path):
        abort(404, "Image not found")
    data = await Storage.get(path)
    ext = path.rsplit(".", 1)[-1].lower()
    media_type = _EXT_CONTENT_TYPE.get(ext, "application/octet-stream")
    return Response(content=data, status=200, headers={"content-type": media_type})


async def serve_image(request: Request) -> Response:
    """Stream the stored original product image (by slug)."""
    product = await Product.where("slug", request.path_param("slug")).first_or_fail()
    return await _serve(product.image_path)


async def serve_thumbnail(request: Request) -> Response:
    """Stream the generated product thumbnail (by slug)."""
    product = await Product.where("slug", request.path_param("slug")).first_or_fail()
    return await _serve(product.image_thumb_path)
