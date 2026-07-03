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
from tests.rbac_helpers import seed_rbac

# a real 1x1 transparent PNG
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'media.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv(
        "FILESYSTEM_LOCAL_ROOT", str(tmp_path / "disk")
    )  # uploads → temp disk

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product):
            model.set_connection(db)
        await seed_rbac(db)
        admin = await User.create(
            name="Admin",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("super-admin")  # catalog.update authority (bypasses)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee"}},
            slug="tee",
            price_cents=2000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        for model in (User, Category, Product):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _auth(client, email, password) -> dict:
    token = client.post(
        "/api/login", json={"email": email, "password": password}
    ).json()["token"]
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

    # the auto-generated thumb + preview conversions are valid, decodable WebP images, served with
    # the matching content-type (derived from the stored extension)
    for conv_url in (item["thumb_url"], item["preview_url"]):
        conv = client.get(conv_url)
        assert conv.status_code == 200 and conv.headers["content-type"] == "image/webp"
        assert PILImage.open(BytesIO(conv.content)).format == "WEBP"


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


def test_admin_deletes_one_gallery_image(client) -> None:
    """S10: DELETE removes ONE image (row + files) and returns the updated gallery; a foreign
    media id 404s and a customer is denied."""
    admin = _auth(client, "admin@example.com", "secret-admin")
    first = client.post(
        "/api/admin/products/1/image",
        files={"image": ("a.png", _PNG, "image/png")},
        headers=admin,
    ).json()[0]
    second = client.post(
        "/api/admin/products/1/image",
        files={"image": ("b.png", _PNG, "image/png")},
        headers=admin,
    ).json()[1]

    # a customer can't delete media
    customer = _auth(client, "cara@example.com", "secret-cara")
    assert (
        client.delete(
            f"/api/admin/products/1/media/{first['id']}", headers=customer
        ).status_code
        == 403
    )

    gallery = client.delete(f"/api/admin/products/1/media/{first['id']}", headers=admin)
    assert gallery.status_code == 200
    assert [g["id"] for g in gallery.json()] == [second["id"]]
    # the deleted original no longer serves
    assert client.get(f"/api/media/{first['id']}").status_code == 404
    # an id that isn't attached to this product → 404
    assert (
        client.delete("/api/admin/products/1/media/999", headers=admin).status_code
        == 404
    )


def test_admin_product_detail_and_translations_update(client) -> None:
    """S10: the editor's read (detail incl. variants+gallery) and per-locale update round-trip."""
    admin = _auth(client, "admin@example.com", "secret-admin")
    detail = client.get("/api/admin/products/1", headers=admin)
    assert detail.status_code == 200
    body = detail.json()
    assert (
        body["price_cents"] == 2000 and body["variants"] == [] and body["gallery"] == []
    )

    updated = client.put(
        "/api/admin/products/1",
        json={
            "published": True,
            "translations": {
                "en": {"name": "Tee", "description": "A tee."},
                "fr": {"name": "T-shirt", "description": "Un t-shirt."},
            },
        },
        headers=admin,
    )
    assert updated.status_code == 200, updated.text
    locales = {t["locale"]: t["name"] for t in updated.json()["translations"]}
    assert locales == {"en": "Tee", "fr": "T-shirt"}

    # the storefront serves the fr content
    fr = client.get("/api/products/tee", headers={"Accept-Language": "fr"})
    assert fr.json()["translation"]["name"] == "T-shirt"

    # an unsupported locale is rejected with a field error
    bad = client.put(
        "/api/admin/products/1",
        json={"translations": {"en": {"name": "Tee"}, "xx": {"name": "nope"}}},
        headers=admin,
    )
    assert bad.status_code == 422 and "translations" in bad.json()["errors"]


def test_admin_media_library_aggregates_every_collection(client) -> None:
    """v6.1 C — GET /api/admin/media is the back-office media library: every stored file
    across products, banners and avatars, with an owner label + link target."""
    admin = _auth(client, "admin@example.com", "secret-admin")
    cara = _auth(client, "cara@example.com", "secret-cara")

    # one product gallery image + one customer avatar
    client.post(
        "/api/admin/products/1/image",
        files={"image": ("shot.png", _PNG, "image/png")},
        headers=admin,
    )
    client.post(
        "/api/account/avatar",
        files={"image": ("face.png", _PNG, "image/png")},
        headers=cara,
    )

    listing = client.get("/api/admin/media", headers=admin)
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 2
    by_collection = {r["collection"]: r for r in rows}
    gallery = by_collection["images"]
    assert gallery["owner_type"] == "product"
    assert gallery["owner_label"] == "Tee"
    assert gallery["url"].startswith("/api/media/")
    assert gallery["size"] > 0 and gallery["mime_type"] == "image/png"
    avatar = by_collection["avatar"]
    assert avatar["owner_type"] == "user" and avatar["owner_label"] == "Cara"

    # permission-guarded: a customer is refused
    assert client.get("/api/admin/media", headers=cara).status_code == 403
