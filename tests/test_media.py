"""Product media — admin image upload to the filesystem disk + public serving, through the real
served path. Uploads land on a temp local disk (FILESYSTEM_LOCAL_ROOT); pointing the disk at
RustFS/S3 is config-only.
"""

import asyncio
import base64

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.user import User

# a real 1x1 transparent PNG
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'media.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("FILESYSTEM_LOCAL_ROOT", str(tmp_path / "disk"))  # uploads → temp disk

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product):
            model.set_connection(db)
        await User.create(name="Admin", email="admin@example.com", password="secret-admin",
                          role=UserRole.ADMIN)
        await User.create(name="Cara", email="cara@example.com", password="secret-cara",
                          role=UserRole.CUSTOMER)
        cat = await Category.create(name="Shirts", slug="shirts")
        await Product.create(category_id=cat.id, name="Tee", slug="tee", price_cents=2000,
                             currency="USD", status=ProductStatus.ACTIVE)
        for model in (User, Category, Product):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _auth(client, email, password) -> dict:
    token = client.post("/api/login", json={"email": email, "password": password}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_uploads_and_image_is_served(client) -> None:
    admin = _auth(client, "admin@example.com", "secret-admin")
    # no image yet → 404
    assert client.get("/api/products/tee/image").status_code == 404

    up = client.post(
        "/api/admin/products/1/image",
        files={"image": ("logo.png", _PNG, "image/png")},
        headers=admin,
    )
    assert up.status_code == 201
    body = up.json()
    assert body["image_path"].startswith("products/")
    assert body["thumb_path"].startswith("products/thumbs/")

    # the original is served back unchanged
    served = client.get("/api/products/tee/image")
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/png")
    assert served.content == _PNG

    # the generated thumbnail (arvel.media) is a valid, decodable PNG
    thumb = client.get("/api/products/tee/thumbnail")
    assert thumb.status_code == 200
    assert thumb.headers["content-type"].startswith("image/png")
    from io import BytesIO

    from PIL import Image as PILImage

    PILImage.open(BytesIO(thumb.content)).verify()  # raises if not a valid image


def test_non_admin_cannot_upload(client) -> None:
    customer = _auth(client, "cara@example.com", "secret-cara")
    resp = client.post(
        "/api/admin/products/1/image",
        files={"image": ("logo.png", _PNG, "image/png")},
        headers=customer,
    )
    assert resp.status_code == 403


def test_rejects_non_image_upload(client) -> None:
    admin = _auth(client, "admin@example.com", "secret-admin")
    resp = client.post(
        "/api/admin/products/1/image",
        files={"image": ("evil.txt", b"not an image", "text/plain")},
        headers=admin,
    )
    assert resp.status_code == 422
