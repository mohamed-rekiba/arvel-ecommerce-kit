"""v6.1 account area through the served path: the address book (CRUD, ownership, single-default
rules, checkout by saved id) and cash-on-delivery (no online pay, ships straight from pending,
still cancellable)."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from tests.rbac_helpers import seed_rbac

_ADDR = {
    "label": "Home",
    "name": "Cara Buyer",
    "line1": "1 Main St",
    "city": "Cairo",
    "postal_code": "11511",
    "country": "EG",
    "phone": "+20 100 000 0000",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'account.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("FILESYSTEM_LOCAL_ROOT", str(tmp_path / "media"))

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        models = (User, Category, Product, ProductVariant)
        for model in models:
            model.set_connection(db)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        await User.create(
            name="Rival",
            email="rival@example.com",
            password="secret-rival",
            role=UserRole.CUSTOMER,
        )
        admin = await User.create(
            name="Ada",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("super-admin")
        cat = await Category.create(
            translations={"en": {"name": "Gear"}}, slug="gear", published=True
        )
        p = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Widget"}},
            slug="widget",
            price_cents=1000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        await ProductVariant.create(
            product_id=p.id, sku="W-1", name="One", price_adjustment_cents=0, stock=50
        )
        for model in models:
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _auth(client, email="cara@example.com", password="secret-cara"):
    token = client.post(
        "/api/login", json={"email": email, "password": password}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_address_book_crud_default_rules_and_ownership(client) -> None:
    cara = _auth(client)
    rival = _auth(client, "rival@example.com", "secret-rival")

    # guests are 401
    assert client.get("/api/account/addresses").status_code == 401

    # the FIRST address becomes the default even when not asked
    first = client.post("/api/account/addresses", json=_ADDR, headers=cara).json()
    assert first["is_default"] is True

    second = client.post(
        "/api/account/addresses",
        json={**_ADDR, "label": "Office", "line1": "9 Work Ave"},
        headers=cara,
    ).json()
    assert second["is_default"] is False

    # promoting the second demotes the first (single default)
    promoted = client.patch(
        f"/api/account/addresses/{second['id']}",
        json={**_ADDR, "label": "Office", "line1": "9 Work Ave", "is_default": True},
        headers=cara,
    ).json()
    assert promoted["is_default"] is True
    rows = client.get("/api/account/addresses", headers=cara).json()
    assert [r["is_default"] for r in rows] == [True, False]  # default sorts first
    assert rows[0]["id"] == second["id"]

    # ownership: the rival can't see, edit, or delete Cara's entries
    assert client.get("/api/account/addresses", headers=rival).json() == []
    assert (
        client.patch(
            f"/api/account/addresses/{first['id']}", json=_ADDR, headers=rival
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/account/addresses/{first['id']}", headers=rival
        ).status_code
        == 404
    )

    # deleting the default promotes the remaining entry
    client.delete(f"/api/account/addresses/{second['id']}", headers=cara)
    rows = client.get("/api/account/addresses", headers=cara).json()
    assert len(rows) == 1 and rows[0]["is_default"] is True


def test_checkout_with_a_saved_address(client) -> None:
    cara = _auth(client)
    addr = client.post("/api/account/addresses", json=_ADDR, headers=cara).json()
    client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}, headers=cara
    )
    order = client.post(
        "/api/checkout", json={"address_id": addr["id"]}, headers=cara
    ).json()
    assert order["address"]["line1"] == "1 Main St"
    assert order["address"]["country"] == "EG"
    assert order["payment_method"] == "gateway"

    # a foreign saved address is a 404 (rival tries Cara's id)
    rival = _auth(client, "rival@example.com", "secret-rival")
    client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}, headers=rival
    )
    assert (
        client.post(
            "/api/checkout", json={"address_id": addr["id"]}, headers=rival
        ).status_code
        == 404
    )


def test_cash_on_delivery_flow(client) -> None:
    cara = _auth(client)
    admin = _auth(client, "admin@example.com", "secret-admin")
    addr = client.post("/api/account/addresses", json=_ADDR, headers=cara).json()
    client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}, headers=cara
    )
    order = client.post(
        "/api/checkout",
        json={"address_id": addr["id"], "payment_method": "cod"},
        headers=cara,
    ).json()
    assert order["payment_method"] == "cod"

    # online pay is refused — nothing to charge
    assert (
        client.post(f"/api/orders/{order['id']}/pay", headers=cara).status_code == 422
    )

    # COD ships straight from PENDING (settled at the door)…
    shipped = client.post(
        f"/api/admin/orders/{order['id']}/status",
        json={"status": "shipped"},
        headers=admin,
    )
    assert shipped.status_code == 200, shipped.text
    assert shipped.json()["status"] == "shipped"

    # …while a GATEWAY order still can't skip payment
    client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}, headers=cara
    )
    gateway_order = client.post(
        "/api/checkout", json={"address_id": addr["id"]}, headers=cara
    ).json()
    refused = client.post(
        f"/api/admin/orders/{gateway_order['id']}/status",
        json={"status": "shipped"},
        headers=admin,
    )
    assert refused.status_code == 422


def test_avatar_upload_and_replace(client) -> None:
    """v6.1: one avatar per account, replace-on-upload; /api/user carries the serving URL."""
    import io

    from PIL import Image as PILImage

    cara = _auth(client)
    assert client.get("/api/user", headers=cara).json()["avatar_url"] is None

    def png(color):
        buf = io.BytesIO()
        PILImage.new("RGB", (64, 64), color).save(buf, format="PNG")
        return buf.getvalue()

    up = client.post(
        "/api/account/avatar",
        files={"image": ("me.png", png((200, 30, 30)), "image/png")},
        headers=cara,
    )
    assert up.status_code == 201, up.text
    first_url = up.json()["avatar_url"]
    assert first_url
    assert client.get("/api/user", headers=cara).json()["avatar_url"] == first_url

    again = client.post(
        "/api/account/avatar",
        files={"image": ("me2.png", png((30, 30, 200)), "image/png")},
        headers=cara,
    )
    assert again.status_code == 201 and again.json()["avatar_url"] != first_url

    bad = client.post(
        "/api/account/avatar",
        files={"image": ("x.txt", b"nope", "text/plain")},
        headers=cara,
    )
    assert bad.status_code == 422
    assert client.post("/api/account/avatar").status_code == 401
