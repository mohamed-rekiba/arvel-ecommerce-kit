"""Checkout & orders through the real served path. Exercises DB transactions (cart→order is
atomic), events (order.placed → the listener bumps a cache counter), and the OrderStatus state
machine (valid transitions allowed, illegal ones 422), with admin-guarded status changes.
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
from tests.rbac_helpers import seed_rbac


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'checkout.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def migrate_and_seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(db)
        await seed_rbac(db)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        admin = await User.create(
            name="Admin",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("super-admin")  # orders.update authority (bypasses)
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

    asyncio.run(migrate_and_seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _login(client, email, password) -> dict:
    token = client.post(
        "/api/login", json={"email": email, "password": password}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_checkout_creates_order_clears_cart_and_fires_event(client) -> None:
    headers = _login(client, "cara@example.com", "secret-cara")
    assert client.get("/api/metrics/orders-placed").json()["orders_placed"] == 0

    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 3},
        headers=headers,
    )

    placed = client.post("/api/checkout", headers=headers)
    assert placed.status_code == 201
    order = placed.json()
    assert order["status"] == "pending"
    assert order["total_cents"] == 6000
    assert order["items"][0]["quantity"] == 3

    # the cart was cleared atomically with the order's creation
    assert client.get("/api/cart", headers=headers).json()["items"] == []
    # the order.placed event fired and its listener bumped the metric (event → listener proven)
    assert client.get("/api/metrics/orders-placed").json()["orders_placed"] == 1
    # the order shows up in the user's order list
    orders = client.get("/api/orders", headers=headers).json()
    assert len(orders) == 1 and orders[0]["id"] == order["id"]


def test_checkout_empty_cart_is_422(client) -> None:
    headers = _login(client, "cara@example.com", "secret-cara")
    assert client.post("/api/checkout", headers=headers).status_code == 422


def test_order_state_machine(client) -> None:
    customer = _login(client, "cara@example.com", "secret-cara")
    admin = _login(client, "admin@example.com", "secret-admin")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=customer,
    )
    order_id = client.post("/api/checkout", headers=customer).json()["id"]

    # a customer cannot change status (admin-only)
    assert (
        client.post(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "paid"},
            headers=customer,
        ).status_code
        == 403
    )

    # illegal transition pending -> delivered is rejected
    assert (
        client.post(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "delivered"},
            headers=admin,
        ).status_code
        == 422
    )

    # legal path: pending -> paid -> shipped -> delivered
    for nxt in ("paid", "shipped", "delivered"):
        resp = client.post(
            f"/api/admin/orders/{order_id}/status", json={"status": nxt}, headers=admin
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == nxt

    # delivered is terminal — no further transition
    assert (
        client.post(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "cancelled"},
            headers=admin,
        ).status_code
        == 422
    )

    # an unknown status is 422
    assert (
        client.post(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "bogus"},
            headers=admin,
        ).status_code
        == 422
    )


def test_admin_lists_all_orders(client) -> None:
    # a customer places an order
    customer = _login(client, "cara@example.com", "secret-cara")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 2},
        headers=customer,
    )
    order_id = client.post("/api/checkout", headers=customer).json()["id"]

    # the admin (orders.view via super-admin) sees it in the back-office list
    admin = _login(client, "admin@example.com", "secret-admin")
    orders = client.get("/api/admin/orders", headers=admin)
    assert orders.status_code == 200
    ids = {o["id"] for o in orders.json()}
    assert order_id in ids

    # a customer cannot list all orders (lacks orders.view)
    assert client.get("/api/admin/orders", headers=customer).status_code == 403


def test_shipping_an_order_notifies_the_customer(client) -> None:
    """The database channel of the notification system: shipping an order stores a notification the
    customer sees in /api/notifications, and mark-read clears the unread state."""
    customer = _login(client, "cara@example.com", "secret-cara")
    admin = _login(client, "admin@example.com", "secret-admin")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=customer,
    )
    order_id = client.post("/api/checkout", headers=customer).json()["id"]

    # no notifications yet
    assert client.get("/api/notifications", headers=customer).json() == []

    # advance pending → paid → shipped (the shipped transition notifies)
    for nxt in ("paid", "shipped"):
        assert (
            client.post(
                f"/api/admin/orders/{order_id}/status",
                json={"status": nxt},
                headers=admin,
            ).status_code
            == 200
        )

    notes = client.get("/api/notifications", headers=customer).json()
    assert len(notes) == 1
    note = notes[0]
    assert note["type"] == "OrderShippedNotification"
    assert f"#{order_id}" in note["message"]
    assert note["read"] is False

    # mark all read
    assert client.post("/api/notifications/read", headers=customer).status_code == 200
    assert client.get("/api/notifications", headers=customer).json()[0]["read"] is True

    # a different customer sees none of it (scoped by notifiable)
    other = _login(client, "admin@example.com", "secret-admin")
    assert client.get("/api/notifications", headers=other).json() == []
