"""v6 — hero banners through the served path: the public carousel feed (active-only, sorted,
projected to the request locale with en fallback), admin CRUD + authz, and the one-image
upload/replace cycle through the media library."""

import asyncio
import io

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import UserRole
from app.models.user import User
from tests.rbac_helpers import seed_rbac


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'banners.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("FILESYSTEM_LOCAL_ROOT", str(tmp_path / "media"))

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        User.set_connection(db)
        _verified_customer = await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        await _verified_customer.mark_email_as_verified()
        admin = await User.create(
            name="Ada",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("super-admin")
        User.set_connection(None)
        await db.dispose()

    asyncio.run(seed())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _auth(client, email="admin@example.com", password="secret-admin"):
    token = client.post(
        "/api/login", json={"email": email, "password": password}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _png() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (32, 14), (200, 120, 40)).save(buf, format="PNG")
    return buf.getvalue()


_PAYLOAD = {
    "translations": {
        "en": {
            "title": "Premium Thermos",
            "subtitle": "Keep warm",
            "chip": "NEW",
            "cta_label": "Shop now",
        },
        "ar": {
            "title": "ترمس فاخر",
            "subtitle": "يحافظ على الحرارة",
            "chip": "جديد",
            "cta_label": "تسوق الآن",
        },
    },
    "cta_to": "/deals",
    "sort": 2,
    "active": True,
}


def test_admin_crud_authz_and_locale_validation(client) -> None:
    customer = _auth(client, "cara@example.com", "secret-cara")
    admin = _auth(client)
    assert (
        client.post("/api/admin/banners", json=_PAYLOAD, headers=customer).status_code
        == 403
    )

    created = client.post("/api/admin/banners", json=_PAYLOAD, headers=admin)
    assert created.status_code == 201, created.text
    banner_id = created.json()["id"]
    assert created.json()["translations"]["ar"]["title"] == "ترمس فاخر"

    # unsupported locale and missing-en are 422s
    bad = {**_PAYLOAD, "translations": {"de": {"title": "Nein"}}}
    assert client.post("/api/admin/banners", json=bad, headers=admin).status_code == 422
    bad = {**_PAYLOAD, "translations": {"fr": {"title": "Sans anglais"}}}
    assert client.post("/api/admin/banners", json=bad, headers=admin).status_code == 422

    updated = client.patch(
        f"/api/admin/banners/{banner_id}",
        json={"sort": 0, "active": False},
        headers=admin,
    )
    assert updated.status_code == 200 and updated.json()["active"] is False

    deleted = client.delete(f"/api/admin/banners/{banner_id}", headers=admin)
    assert deleted.status_code in (200, 204)
    assert client.get("/api/admin/banners", headers=admin).json() == []


def test_public_feed_is_active_sorted_and_localized(client) -> None:
    admin = _auth(client)
    client.post("/api/admin/banners", json=_PAYLOAD, headers=admin)  # sort 2
    first = {
        **_PAYLOAD,
        "sort": 1,
        "translations": {"en": {"title": "Big Friday", "cta_label": "Grab it"}},
    }
    client.post("/api/admin/banners", json=first, headers=admin)
    hidden = {**_PAYLOAD, "active": False, "translations": {"en": {"title": "Hidden"}}}
    client.post("/api/admin/banners", json=hidden, headers=admin)

    feed = client.get("/api/banners").json()
    assert [b["title"] for b in feed] == [
        "Big Friday",
        "Premium Thermos",
    ]  # active, sort order
    assert feed[1]["cta_to"] == "/deals"

    # locale projection + en fallback for a slide without that locale
    ar = client.get("/api/banners", headers={"Accept-Language": "ar"}).json()
    assert ar[1]["title"] == "ترمس فاخر"
    assert ar[0]["title"] == "Big Friday"  # no ar copy → en fallback


def test_image_upload_and_replace(client) -> None:
    admin = _auth(client)
    banner_id = client.post("/api/admin/banners", json=_PAYLOAD, headers=admin).json()[
        "id"
    ]
    assert client.get("/api/banners").json()[0]["image_url"] is None

    up = client.post(
        f"/api/admin/banners/{banner_id}/image",
        files={"image": ("hero.png", _png(), "image/png")},
        headers=admin,
    )
    assert up.status_code == 201, up.text
    url_one = up.json()["image_url"]
    assert url_one
    public = client.get("/api/banners").json()[0]
    assert public["image_url"] and public["mobile_image_url"]

    # replacing swaps the media (one image per slide)
    again = client.post(
        f"/api/admin/banners/{banner_id}/image",
        files={"image": ("hero2.png", _png(), "image/png")},
        headers=admin,
    )
    assert again.status_code == 201 and again.json()["image_url"] != url_one

    # garbage is a 422, not a 500
    bad = client.post(
        f"/api/admin/banners/{banner_id}/image",
        files={"image": ("nope.txt", b"not an image", "text/plain")},
        headers=admin,
    )
    assert bad.status_code == 422
