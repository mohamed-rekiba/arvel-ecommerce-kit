"""S12 — archive/restore (SoftDeletes) through the served path: delete archives (recoverable,
order history intact), archived items leave the storefront and default admin lists, restore
returns them with visibility semantics intact, and carted/checkout edges are deterministic."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.shipping_method import ShippingMethod
from app.models.user import User
from tests.checkout_helpers import checkout_body
from tests.rbac_helpers import seed_rbac


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'soft.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        for model in (User, Category, Product, ProductVariant, ShippingMethod):
            model.set_connection(db)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
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
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        p = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee"}},
            slug="tee",
            price_cents=2000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        await ProductVariant.create(
            product_id=p.id, sku="TEE-S", name="S", price_adjustment_cents=0, stock=50
        )
        await ShippingMethod.create(
            code="standard", name="Standard", rate_cents=500, active=True, sort=0
        )
        for model in (User, Category, Product, ProductVariant, ShippingMethod):
            model.set_connection(None)
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


def test_archive_hides_restore_returns_with_visibility_intact(client) -> None:
    admin = _auth(client)

    # the customer orders it first — history must survive archival
    customer = _auth(client, "cara@example.com", "secret-cara")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=customer,
    )
    order = client.post("/api/checkout", json=checkout_body(), headers=customer).json()

    # archive: gone from the storefront + the default admin list; present in archived=true
    assert client.delete("/api/admin/products/1", headers=admin).status_code == 200
    assert client.get("/api/products/tee").status_code == 404
    default_ids = [
        p["id"] for p in client.get("/api/admin/products", headers=admin).json()["data"]
    ]
    assert 1 not in default_ids
    archived = client.get("/api/admin/products?archived=true", headers=admin).json()[
        "data"
    ]
    assert [p["id"] for p in archived] == [1]

    # order history intact: the customer still sees the line with its snapshot name
    detail = client.get(f"/api/orders/{order['id']}", headers=customer).json()
    assert detail["items"][0]["product_name"] == "Tee"

    # the archived slug can't be silently reused
    dup = client.post(
        "/api/admin/products",
        json={
            "category_id": 1,
            "price_cents": 900,
            "translations": {"en": {"name": "Tee"}},
        },
        headers=admin,
    )
    assert dup.status_code == 422 and "slug" in dup.json()["errors"]

    # restore: back on the storefront (it was published → visible again)
    restored = client.post("/api/admin/products/1/restore", headers=admin)
    assert restored.status_code == 200
    assert client.get("/api/products/tee").status_code == 200

    # a hidden product restores hidden: unpublish, archive, restore → still off the storefront
    client.put("/api/admin/products/1", json={"published": False}, headers=admin)
    client.delete("/api/admin/products/1", headers=admin)
    client.post("/api/admin/products/1/restore", headers=admin)
    assert client.get("/api/products/tee").status_code == 404


def test_archived_product_in_a_cart_fails_checkout_cleanly(client) -> None:
    admin = _auth(client)
    customer = _auth(client, "cara@example.com", "secret-cara")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=customer,
    )

    # archived AFTER carting → checkout refuses deterministically (409, clear message, no order)
    client.delete("/api/admin/products/1", headers=admin)
    resp = client.post("/api/checkout", json=checkout_body(), headers=customer)
    assert resp.status_code == 409
    assert "no longer available" in resp.json()["errors"]["product_variant_id"][0]
    assert client.get("/api/orders", headers=customer).json() == []
