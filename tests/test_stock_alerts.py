"""S17 — back-in-stock alerts through the served path: subscribe rules, the 0→positive edge,
one-shot consumption, and no re-notification on later adjustments."""

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
    url = f"sqlite+aiosqlite:///{tmp_path / 'alerts.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(db)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        await User.create(
            name="Noah",
            email="noah@example.com",
            password="secret-noah",
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
            product_id=p.id, sku="TEE-S", name="S", price_adjustment_cents=0, stock=0
        )
        await ProductVariant.create(
            product_id=p.id, sku="TEE-M", name="M", price_adjustment_cents=0, stock=9
        )
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _wait_for(check, attempts=40, delay=0.05):
    """The memory broker schedules queued jobs on the running loop — a POST can return before the
    fan-out job has run. Poll briefly instead of asserting instantly (the integration tier does the
    same with a real worker via `_run_worker(until=...)`)."""
    import time

    for _ in range(attempts):
        if check():
            return True
        time.sleep(delay)
    return check()


def _auth(client, email, password):
    token = client.post(
        "/api/login", json={"email": email, "password": password}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_restock_edge_notifies_subscribers_exactly_once(client) -> None:
    cara = _auth(client, "cara@example.com", "secret-cara")
    noah = _auth(client, "noah@example.com", "secret-noah")
    admin = _auth(client, "admin@example.com", "secret-admin")

    # in-stock variant → 422; sold-out subscribes; duplicate is an idempotent 200; guests 401
    assert client.post("/api/variants/2/stock-alert", headers=cara).status_code == 422
    assert client.post("/api/variants/1/stock-alert", headers=cara).status_code == 200
    assert client.post("/api/variants/1/stock-alert", headers=cara).status_code == 200
    assert client.post("/api/variants/1/stock-alert", headers=noah).status_code == 200
    assert client.post("/api/variants/1/stock-alert").status_code == 401

    # restock 0→7 → both subscribers get the database notification (mail leg covered in integration)
    client.post(
        "/api/admin/variants/1/stock",
        json={"set": 7, "reason": "restock"},
        headers=admin,
    )
    for headers in (cara, noah):
        assert _wait_for(
            lambda h=headers: (
                [n["type"] for n in client.get("/api/notifications", headers=h).json()]
                == ["BackInStockNotification"]
            )
        )
        notes = client.get("/api/notifications", headers=headers).json()
        assert "back in stock" in notes[0]["message"]

    # a second adjustment while already >0 does NOT re-notify (edge-triggered + one-shot)
    client.post(
        "/api/admin/variants/1/stock", json={"set": 20, "reason": "more"}, headers=admin
    )
    # even a fresh 0→positive cycle is quiet — the subscriptions were consumed
    client.post("/api/admin/variants/1/stock", json={"set": 0}, headers=admin)
    client.post("/api/admin/variants/1/stock", json={"set": 5}, headers=admin)
    import time

    time.sleep(
        0.3
    )  # give any (wrongly) queued job the chance to land before asserting silence
    assert len(client.get("/api/notifications", headers=cara).json()) == 1
    assert len(client.get("/api/notifications", headers=noah).json()) == 1


def test_unsubscribe_prevents_the_alert(client) -> None:
    cara = _auth(client, "cara@example.com", "secret-cara")
    admin = _auth(client, "admin@example.com", "secret-admin")
    client.post("/api/variants/1/stock-alert", headers=cara)
    client.delete("/api/variants/1/stock-alert", headers=cara)
    client.post("/api/admin/variants/1/stock", json={"set": 3}, headers=admin)
    import time

    time.sleep(0.3)
    assert client.get("/api/notifications", headers=cara).json() == []
