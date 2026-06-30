"""Product media — admin image upload (stored on the filesystem disk) + public serving.

Exercises arvel's filesystem (Storage / UploadedFile.store) and multipart request handling. The
default disk is `local`; pointing FILESYSTEM_DISK=s3 at a RustFS/S3 store needs no code change.
"""

from typing import Any

from arvel import Storage, abort
from arvel.http import Response
from arvel.support import current_user

from app.models.product import Product

_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
_EXT_CONTENT_TYPE = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}


async def upload_image(request) -> Any:
    """POST /api/admin/products/{id}/image — store an uploaded image (admins only)."""
    user = current_user.get()
    if user is None or not user.is_admin():
        abort(403, "Only admins may upload product images.")
    product = await Product.find(int(request.path_param("id")))
    if product is None:
        abort(404, "Product not found")
    upload = await request.file("image")
    if upload is None:
        abort(422, {"image": ["An image file is required."]})
    if upload.content_type not in _ALLOWED_IMAGE_TYPES:
        abort(422, {"image": [f"Unsupported image type '{upload.content_type}'."]})

    # store under a hashed name on the default disk; returns the stored path
    path = await upload.store("products")
    product.image_path = path
    await product.save()
    return Response(content={"image_path": path}, status=201)


async def serve_image(request) -> Any:
    """GET /api/products/{slug}/image — stream the stored product image."""
    product = await Product.query().where("slug", request.path_param("slug")).first()
    if product is None or not product.image_path:
        abort(404, "Image not found")
    if not await Storage.exists(product.image_path):
        abort(404, "Image not found")
    data = await Storage.get(product.image_path)
    ext = product.image_path.rsplit(".", 1)[-1].lower()
    media_type = _EXT_CONTENT_TYPE.get(ext, "application/octet-stream")
    return Response(content=data, status=200, headers={"content-type": media_type})
