"""v6 — deals (flash sales) through the served path: the active-window listing with sold/available
aggregates, deal-aware product payloads, REAL pricing (cart snapshots the deal price; checkout
re-prices every line to the CURRENT price — an expired deal never leaks into an order, a new deal
is honored), and admin CRUD + authz."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations
from arvel.dates import Date

from app.enums import OrderStatus, ProductStatus, UserRole
from app.models.category import Category
from app.models.deal import Deal
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from tests.checkout_helpers import checkout_body
from tests.rbac_helpers import seed_rbac


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'deals.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        models = (User, Category, Product, ProductVariant, Deal, Order, OrderItem)
        for model in models:
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
            translations={"en": {"name": "Bottles"}}, slug="bottles", published=True
        )
        dealp = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Thermos"}},
            slug="thermos",
            price_cents=4000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        plain = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Mug"}},
            slug="mug",
            price_cents=1000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        await ProductVariant.create(
            product_id=dealp.id, sku="TH-500", name="500ml", price_adjustment_cents=0, stock=18
        )
        await ProductVariant.create(
            product_id=dealp.id,
            sku="TH-750",
            name="750ml",
            price_adjustment_cents=1000,
            stock=7,
        )
        await ProductVariant.create(
            product_id=plain.id, sku="MUG-1", name="One", price_adjustment_cents=0, stock=50
        )
        now = Date.now()
        # the deal zoo: one live, one expired, one future, one inactive
        await Deal.create(
            product_id=dealp.id,
            percent_off=25,
            starts_at=now.subtract(hours=1),
            ends_at=now.add(hours=23),
            active=True,
        )
        await Deal.create(
            product_id=plain.id,
            percent_off=50,
            starts_at=now.subtract(days=3),
            ends_at=now.subtract(days=1),
            active=True,
        )
        await Deal.create(
            product_id=plain.id,
            percent_off=40,
            starts_at=now.add(days=1),
            ends_at=now.add(days=2),
            active=True,
        )
        await Deal.create(
            product_id=plain.id,
            percent_off=30,
            starts_at=now.subtract(hours=1),
            ends_at=now.add(hours=1),
            active=False,
        )
        # sold history for the aggregate: 42 sold on a PAID order, 5 on a CANCELLED one (ignored)
        paid = await Order.create(
            user_id=1,
            status=OrderStatus.PAID,
            contact_email="cara@example.com",
            token="tok-paid",
            ship_name="C",
            ship_line1="1 St",
            ship_city="X",
            ship_postal_code="1",
            ship_country="US",
            subtotal_cents=0,
            shipping_cents=0,
            tax_cents=0,
            total_cents=0,
            currency="USD",
        )
        await OrderItem.create(
            order_id=paid.id,
            product_variant_id=1,
            product_name="Thermos",
            variant_name="500ml",
            quantity=42,
            unit_price_cents=3000,
        )
        cancelled = await Order.create(
            user_id=1,
            status=OrderStatus.CANCELLED,
            contact_email="cara@example.com",
            token="tok-x",
            ship_name="C",
            ship_line1="1 St",
            ship_city="X",
            ship_postal_code="1",
            ship_country="US",
            subtotal_cents=0,
            shipping_cents=0,
            tax_cents=0,
            total_cents=0,
            currency="USD",
        )
        await OrderItem.create(
            order_id=cancelled.id,
            product_variant_id=1,
            product_name="Thermos",
            variant_name="500ml",
            quantity=5,
            unit_price_cents=3000,
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


def test_deals_index_lists_only_live_window_deals(client) -> None:
    deals = client.get("/api/deals").json()
    assert len(deals) == 1
    deal = deals[0]
    assert deal["percent_off"] == 25
    assert deal["product"]["slug"] == "thermos"
    # 25% off the base 4000 → 3000
    assert deal["deal_price_cents"] == 3000
    assert deal["ends_at"]
    # availability = Σ variant stock; sold counts only completed-path orders
    assert deal["available"] == 25
    assert deal["sold"] == 42


def test_product_payload_carries_the_active_deal(client) -> None:
    body = client.get("/api/products/thermos").json()
    assert body["deal"]["percent_off"] == 25
    assert body["deal"]["deal_price_cents"] == 3000
    # a product without a live deal (expired/future/inactive don't count) → null
    assert client.get("/api/products/mug").json()["deal"] is None
    listing = {p["slug"]: p for p in client.get("/api/products").json()["data"]}
    assert listing["thermos"]["deal"]["percent_off"] == 25
    assert listing["mug"]["deal"] is None


def test_cart_snapshots_the_deal_price(client) -> None:
    headers = _auth(client)
    cart = client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 2},
        headers=headers,
    ).json()
    assert cart["items"][0]["unit_price_cents"] == 3000  # deal price, not 4000
    # variant price adjustments participate in the discount base: (4000+1000)*0.75 = 3750
    cart = client.post(
        "/api/cart/items",
        json={"product_variant_id": 2, "quantity": 1},
        headers=headers,
    ).json()
    by_variant = {i["product_variant_id"]: i for i in cart["items"]}
    assert by_variant[2]["unit_price_cents"] == 3750


def test_checkout_reprices_to_the_current_price(client) -> None:
    """The line was added at the deal price; the deal ends before checkout → the order charges
    the CURRENT (base) price. Current-price-wins, both directions."""
    headers = _auth(client)
    client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}, headers=headers
    )

    async def _expire() -> None:
        await Deal.where("percent_off", 25).update(
            {"ends_at": Date.now().subtract(minutes=5)}
        )

    with client.portal() as portal:
        portal.call(_expire)
    order = client.post("/api/checkout", json=checkout_body(), headers=headers).json()
    assert order["subtotal_cents"] == 4000  # base price, not the stale 3000 snapshot


def test_checkout_honors_a_deal_that_started_after_add(client) -> None:
    headers = _auth(client)
    client.post(
        "/api/cart/items", json={"product_variant_id": 3, "quantity": 2}, headers=headers
    )  # mug at base 1000

    async def _start_deal() -> None:
        now = Date.now()
        await Deal.create(
            product_id=2,
            percent_off=10,
            starts_at=now.subtract(minutes=1),
            ends_at=now.add(hours=1),
            active=True,
        )

    with client.portal() as portal:
        portal.call(_start_deal)
    order = client.post("/api/checkout", json=checkout_body(), headers=headers).json()
    assert order["subtotal_cents"] == 1800  # 2 × 900 (current deal price wins)


def test_admin_crud_and_authz(client) -> None:
    admin = _auth(client, "admin@example.com", "secret-admin")
    customer = _auth(client)
    now = Date.now()
    payload = {
        "product_id": 2,
        "percent_off": 15,
        "starts_at": now.subtract(hours=1).to_iso(),
        "ends_at": now.add(hours=4).to_iso(),
        "active": True,
    }
    # customers can't manage deals
    assert client.post("/api/admin/deals", json=payload, headers=customer).status_code == 403
    created = client.post("/api/admin/deals", json=payload, headers=admin)
    assert created.status_code == 201, created.text
    deal_id = created.json()["id"]
    assert created.json()["percent_off"] == 15

    # percent bounds are validated
    bad = client.post(
        "/api/admin/deals", json={**payload, "percent_off": 95}, headers=admin
    )
    assert bad.status_code == 422

    # the admin index shows every deal (incl. inactive/expired); the update flips active
    listed = client.get("/api/admin/deals", headers=admin).json()
    assert any(d["id"] == deal_id for d in listed)
    updated = client.patch(
        f"/api/admin/deals/{deal_id}", json={"active": False}, headers=admin
    )
    assert updated.status_code == 200 and updated.json()["active"] is False

    deleted = client.delete(f"/api/admin/deals/{deal_id}", headers=admin)
    assert deleted.status_code in (200, 204)
    assert not any(
        d["id"] == deal_id
        for d in client.get("/api/admin/deals", headers=admin).json()
    )
