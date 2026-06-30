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
        cat = await Category.create(translations={"en": {"name": "Shirts"}}, slug="shirts", published=True)
        await Product.create(category_id=cat.id, translations={"en": {"name": "Tee"}}, slug="tee", price_cents=2000,
                             currency="USD", status=ProductStatus.ACTIVE, published=True)
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


def test_admin_uploads_to_gallery_and_media_is_served(client) -> None:
    from io import BytesIO

    from PIL import Image as PILImage

    admin = _auth(client, "admin@example.com", "secret-admin")
    # product starts with an empty gallery
    assert client.get("/api/products/tee").json()["gallery"] == []

    up = client.post(
        "/api/admin/products/1/image",
        files={"image": ("logo.png", _PNG, "image/png")},
        headers=admin,
    )
    assert up.status_code == 201
    gallery = up.json()
    assert len(gallery) == 1
    item = gallery[0]
    assert item["url"] == f"/api/media/{item['id']}"

    # the product now exposes the gallery
    assert len(client.get("/api/products/tee").json()["gallery"]) == 1

    # the original media serves back unchanged
    original = client.get(item["url"])
    assert original.status_code == 200 and original.content == _PNG

    # the auto-generated thumb + preview conversions are valid, decodable PNGs
    for conv_url in (item["thumb_url"], item["preview_url"]):
        conv = client.get(conv_url)
        assert conv.status_code == 200 and conv.headers["content-type"] == "image/png"
        PILImage.open(BytesIO(conv.content)).verify()


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
