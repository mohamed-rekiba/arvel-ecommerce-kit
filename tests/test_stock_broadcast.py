"""K9 — `StockChanged` fires once, through the one `broadcast_stock()` helper, on an admin stock
adjustment (the log driver records it here; the redis push is proven at the integration tier)."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations
from arvel.kernel import Application

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from tests.rbac_helpers import seed_rbac


@pytest.fixture
def app_and_client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'stock_broadcast.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        from app.models.user import User

        for model in (User, Category, Product, ProductVariant):
            model.set_connection(db)
        admin = await User.create(
            name="Cat",
            email="catalog@example.com",
            password="secret-catalog",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("catalog-manager")
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
            product_id=p.id, sku="TEE-S", name="S", price_adjustment_cents=0, stock=5
        )
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())
    from bootstrap.app import create_app

    app: Application = create_app()
    with TestClient(app=app.as_asgi()) as test_client:
        yield app, test_client


def _auth(client) -> dict:
    token = client.post(
        "/api/login",
        json={"email": "catalog@example.com", "password": "secret-catalog"},
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_adjust_stock_broadcasts_stock_changed_on_the_public_variant_channel(
    app_and_client,
) -> None:
    app, client = app_and_client
    admin = _auth(client)

    resp = client.post(
        "/api/admin/products/1/variants/1/stock",
        json={"set": 12},
        headers=admin,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["stock"] == 12
    # the broadcast rides the queue (the "memory" driver's task is fire-and-forget); one more
    # request gives the event loop the turns it needs to finish that task first.
    client.get("/api/products/tee")

    sent = app.make("broadcast").sent
    matches = [s for s in sent if s[0] == "StockChanged"]
    assert len(matches) == 1, sent
    _event_name, channels, event = matches[0]
    assert channels == ["stock.1"]
    assert event.broadcast_with() == {"variant_id": 1, "stock": 12, "in_stock": True}


def test_adjust_stock_to_zero_reports_out_of_stock(app_and_client) -> None:
    app, client = app_and_client
    admin = _auth(client)

    client.post(
        "/api/admin/products/1/variants/1/stock", json={"set": 0}, headers=admin
    )
    client.get("/api/products/tee")  # let the queued broadcast task finish first

    sent = app.make("broadcast").sent
    _event_name, _channels, event = [s for s in sent if s[0] == "StockChanged"][-1]
    assert event.broadcast_with() == {"variant_id": 1, "stock": 0, "in_stock": False}
