"""S8 — guest→user cart merge on login/register, through the served path: union + sum-with-stock-
cap semantics, no-op edges, and the foreign-token guard."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'merge.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(db)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
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
            product_id=p.id, sku="TEE-S", name="S", price_adjustment_cents=0, stock=3
        )
        await ProductVariant.create(
            product_id=p.id, sku="TEE-M", name="M", price_adjustment_cents=0, stock=50
        )
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _login(client, headers=None):
    return client.post(
        "/api/login",
        json={"email": "cara@example.com", "password": "secret-cara"},
        headers=headers or {},
    )


def test_login_merges_the_guest_cart(client) -> None:
    """Union + sum-cap: the user already holds 2×S (stock 3); the guest adds 2×S and 1×M.
    After login: S capped at 3, M joins — and the guest token no longer resolves a cart."""
    # the user's existing cart: 2×S
    auth = {"Authorization": f"Bearer {_login(client).json()['token']}"}
    client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 2}, headers=auth
    )

    # a guest cart: 2×S + 1×M
    guest_token = client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 2}
    ).json()["cart_token"]
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 2, "quantity": 1},
        headers={"X-Cart-Token": guest_token},
    )

    # sign in WITH the guest token on the request → merge
    merged_auth = {
        "Authorization": f"Bearer {_login(client, {'X-Cart-Token': guest_token}).json()['token']}"
    }
    cart = client.get("/api/cart", headers=merged_auth).json()
    by_variant = {
        line["product_variant_id"]: line["quantity"] for line in cart["items"]
    }
    assert by_variant == {1: 3, 2: 1}  # 2+2 capped at stock 3; M unioned

    # the guest token is retired: it no longer resolves to a live cart
    assert (
        client.get("/api/cart", headers={"X-Cart-Token": guest_token}).json()["items"]
        == []
    )


def test_register_merges_and_empty_or_foreign_tokens_are_noops(client) -> None:
    # a guest cart that will follow the registration
    guest_token = client.post(
        "/api/cart/items", json={"product_variant_id": 2, "quantity": 4}
    ).json()["cart_token"]
    reg = client.post(
        "/api/register",
        json={"name": "New", "email": "new@example.com", "password": "supersecret"},
        headers={"X-Cart-Token": guest_token},
    )
    auth = {"Authorization": f"Bearer {reg.json()['token']}"}
    cart = client.get("/api/cart", headers=auth).json()
    assert [
        (line["product_variant_id"], line["quantity"]) for line in cart["items"]
    ] == [(2, 4)]

    # login with NO token and with a bogus token: the user's cart is untouched
    for headers in ({}, {"X-Cart-Token": "bogus-token"}):
        again = {
            "Authorization": f"Bearer {client.post('/api/login', json={'email': 'new@example.com', 'password': 'supersecret'}, headers=headers).json()['token']}"
        }
        cart = client.get("/api/cart", headers=again).json()
        assert [
            (line["product_variant_id"], line["quantity"]) for line in cart["items"]
        ] == [(2, 4)]
