"""Inventory — stock is decremented atomically at checkout and oversell is rejected (and rolls
back). The row-lock that prevents *concurrent* oversell is a no-op on SQLite, so the true race is
proven against Postgres in arvel's integration tier; here we prove the decrement + the oversell
guard + the transactional rollback on the real served path.
"""

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


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'inventory.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product, ProductVariant, ShippingMethod):
            model.set_connection(db)
        _verified_customer = await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        await _verified_customer.mark_email_as_verified()
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        p = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee"}},
            slug="tee",
            price_cents=1000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        await ProductVariant.create(
            product_id=p.id, sku="TEE-S", name="S", price_adjustment_cents=0, stock=5
        )  # only 5 in stock
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


def _login(client) -> dict:
    token = client.post(
        "/api/login", json={"email": "cara@example.com", "password": "secret-cara"}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _variant_stock(client) -> int:
    return client.get("/api/products/tee").json()["variants"][0]["stock"]


def test_checkout_decrements_stock(client) -> None:
    headers = _login(client)
    assert _variant_stock(client) == 5
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 3},
        headers=headers,
    )
    assert (
        client.post("/api/checkout", json=checkout_body(), headers=headers).status_code
        == 201
    )
    assert _variant_stock(client) == 2  # 5 - 3


def test_oversell_is_rejected_and_rolls_back(client) -> None:
    headers = _login(client)
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 9},
        headers=headers,
    )
    resp = client.post("/api/checkout", json=checkout_body(), headers=headers)
    assert resp.status_code == 409  # insufficient stock
    # rolled back: stock untouched, no order placed, cart intact
    assert _variant_stock(client) == 5
    assert client.get("/api/orders", headers=headers).json() == []
    assert client.get("/api/cart", headers=headers).json()["items"][0]["quantity"] == 9
