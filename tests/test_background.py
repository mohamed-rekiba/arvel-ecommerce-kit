"""Background processing + scheduling. The queued FulfillOrderJob runs on the (in-process memory)
broker when an order is placed; the abandoned-cart sweep (a scheduled task) deletes stale guest
carts. The memory broker runs jobs inline on dispatch, so the job's effect is observable.
"""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.dates import Date
from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.console.abandoned_carts import sweep_abandoned_carts
from app.enums import ProductStatus, UserRole
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from tests.checkout_helpers import checkout_body


@pytest.fixture
def db_url(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'bg.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)
    return url


@pytest.fixture
def client(db_url):
    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": db_url}})
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
            translations={"en": {"name": "Shirts"}}, slug="shirts"
        )
        p = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee"}},
            slug="tee",
            price_cents=2000,
            currency="USD",
            status=ProductStatus.ACTIVE,
        )
        await ProductVariant.create(
            product_id=p.id, sku="TEE-S", name="S", price_adjustment_cents=0, stock=100
        )
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def test_checkout_queues_and_runs_the_fulfillment_job(client) -> None:
    token = client.post(
        "/api/login", json={"email": "cara@example.com", "password": "secret-cara"}
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/metrics/orders-placed").json()["orders_fulfilled"] == 0
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=headers,
    )
    assert client.post("/api/checkout", json=checkout_body(), headers=headers).status_code == 201
    # the FulfillOrderJob was dispatched and ran on the memory broker (inline)
    assert client.get("/api/metrics/orders-placed").json()["orders_fulfilled"] == 1


async def test_abandoned_cart_sweep_deletes_stale_guest_carts(db_url) -> None:
    db = ConnectionResolver({"default": {"url": db_url}})
    await Migrator(db).run(discover_migrations(["database/migrations"]))
    for model in (Cart, CartItem):
        model.set_connection(db)
    try:
        # a fresh guest cart and a stale one (updated 100h ago)
        fresh = await Cart.create(token="fresh")
        stale = await Cart.create(token="stale")
        await CartItem.create(
            cart_id=stale.id, product_variant_id=1, quantity=1, unit_price_cents=1000
        )
        old = Date.now().subtract(hours=100)
        # backdate updated_at directly (the model auto-manages it on save) via the query builder
        await Cart.where("id", stale.id).update({"updated_at": old})
        # an authenticated user's cart is never swept, even if old
        user_cart = await Cart.create(user_id=1)
        await Cart.where("id", user_cart.id).update({"updated_at": old})

        swept = await sweep_abandoned_carts(older_than_hours=72)

        assert swept == 1
        assert await Cart.find(stale.id) is None  # stale guest cart gone
        assert await Cart.find(fresh.id) is not None  # fresh guest cart kept
        assert await Cart.find(user_cart.id) is not None  # user cart kept
    finally:
        for model in (Cart, CartItem):
            model.set_connection(None)
        await db.dispose()
