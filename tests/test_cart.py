"""Cart API — guest (cart-token) and authenticated carts through the real served path. Exercises
the ORM (relations), the Cache facade (subtotal cached + invalidated on mutation), and request
handling. Guest carts round-trip an X-Cart-Token; an authenticated user's cart follows the user.
"""

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
    url = f"sqlite+aiosqlite:///{tmp_path / 'cart.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def migrate_and_seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(db)
        await User.create(name="Cara", email="cara@example.com", password="secret-cara",
                          role=UserRole.CUSTOMER)
        cat = await Category.create(translations={"en": {"name": "Shirts"}}, slug="shirts")
        p = await Product.create(category_id=cat.id, translations={"en": {"name": "Tee"}}, slug="tee",
                                 price_cents=2000, currency="USD", status=ProductStatus.ACTIVE)
        # variant 1: +0 adjustment (unit 2000); variant 2: +500 (unit 2500)
        await ProductVariant.create(product_id=p.id, sku="TEE-S", name="S",
                                    price_adjustment_cents=0, stock=100)
        await ProductVariant.create(product_id=p.id, sku="TEE-L", name="L",
                                    price_adjustment_cents=500, stock=100)
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(migrate_and_seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _login(client) -> str:
    return client.post(
        "/api/login", json={"email": "cara@example.com", "password": "secret-cara"}
    ).json()["token"]


def test_guest_cart_round_trips_a_token_and_totals(client) -> None:
    # empty cart for a brand-new guest
    assert client.get("/api/cart").json() == {"id": None, "items": [], "total_cents": 0}

    # add variant 1 (unit 2000) x2 → a cart token is returned
    add = client.post("/api/cart/items", json={"product_variant_id": 1, "quantity": 2})
    assert add.status_code == 201
    body = add.json()
    token = body["cart_token"]
    assert body["total_cents"] == 4000
    assert body["items"][0]["line_total_cents"] == 4000

    headers = {"X-Cart-Token": token}
    # add variant 2 (unit 2500) x1 → total 4000 + 2500 = 6500 (cached total invalidated)
    add2 = client.post(
        "/api/cart/items", json={"product_variant_id": 2, "quantity": 1}, headers=headers
    )
    assert add2.json()["total_cents"] == 6500

    # GET with the token returns the same cart
    got = client.get("/api/cart", headers=headers)
    assert got.json()["total_cents"] == 6500
    assert len(got.json()["items"]) == 2

    # adding the same variant again bumps quantity, not a new line
    again = client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}, headers=headers
    )
    assert len(again.json()["items"]) == 2
    assert again.json()["total_cents"] == 6500 + 2000


def test_update_and_remove_items(client) -> None:
    token = client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}
    ).json()["cart_token"]
    headers = {"X-Cart-Token": token}
    item_id = client.get("/api/cart", headers=headers).json()["items"][0]["id"]

    # bump quantity to 3 → total 6000
    upd = client.patch(f"/api/cart/items/{item_id}", json={"quantity": 3}, headers=headers)
    assert upd.json()["total_cents"] == 6000

    # quantity 0 removes the line
    zero = client.patch(f"/api/cart/items/{item_id}", json={"quantity": 0}, headers=headers)
    assert zero.json()["items"] == []
    assert zero.json()["total_cents"] == 0


def test_authenticated_cart_follows_the_user(client) -> None:
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/cart/items", json={"product_variant_id": 2, "quantity": 2}, headers=headers)
    # a fresh request (no cart token) still finds the user's cart
    got = client.get("/api/cart", headers=headers)
    assert got.json()["total_cents"] == 5000  # 2500 x 2
    # an authenticated add does NOT return a guest cart token
    assert "cart_token" not in got.json()


def test_add_unknown_variant_404(client) -> None:
    assert client.post("/api/cart/items", json={"product_variant_id": 999, "quantity": 1}).status_code == 404
