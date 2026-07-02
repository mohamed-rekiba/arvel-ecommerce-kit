"""S15 — coupons through the served path: percent/fixed math on the breakdown, every distinct
rejection reason, checkout re-validation (a stale cart discount never leaks into an order),
merge semantics, and admin CRUD + authz."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations
from arvel.dates import Date

from app.enums import CouponType, ProductStatus, UserRole
from app.models.category import Category
from app.models.coupon import Coupon
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from tests.checkout_helpers import checkout_body
from tests.rbac_helpers import seed_rbac


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'coupons.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        for model in (User, Category, Product, ProductVariant, Coupon):
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
        support = await User.create(
            name="Sup",
            email="support@example.com",
            password="secret-support",
            role=UserRole.ADMIN,
        )
        await support.assign_role("support")
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
            product_id=p.id, sku="TEE-S", name="S", price_adjustment_cents=0, stock=100
        )
        # the coupon zoo
        await Coupon.create(
            code="TEN", type=CouponType.PERCENT, value=10, uses=0, active=True
        )
        await Coupon.create(
            code="FIVER", type=CouponType.FIXED, value=500, uses=0, active=True
        )
        await Coupon.create(
            code="BIG", type=CouponType.FIXED, value=999999, uses=0, active=True
        )  # bigger than any subtotal
        await Coupon.create(
            code="MIN50",
            type=CouponType.PERCENT,
            value=10,
            min_subtotal_cents=5000,
            uses=0,
            active=True,
        )
        await Coupon.create(
            code="OFF", type=CouponType.PERCENT, value=10, uses=0, active=False
        )
        await Coupon.create(
            code="GONE",
            type=CouponType.PERCENT,
            value=10,
            usage_limit=1,
            uses=1,
            active=True,
        )
        await Coupon.create(
            code="LATER",
            type=CouponType.PERCENT,
            value=10,
            starts_at=Date.now().add(days=2),
            uses=0,
            active=True,
        )
        await Coupon.create(
            code="PAST",
            type=CouponType.PERCENT,
            value=10,
            ends_at=Date.now().subtract(days=2),
            uses=0,
            active=True,
        )
        await Coupon.create(
            code="ONCE",
            type=CouponType.PERCENT,
            value=10,
            per_customer_limit=1,
            uses=0,
            active=True,
        )
        for model in (User, Category, Product, ProductVariant, Coupon):
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


def _fill_cart(client, headers, qty=1):
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": qty},
        headers=headers,
    )


def test_percent_and_fixed_discounts_flow_into_the_order(client) -> None:
    cara = _auth(client)
    _fill_cart(client, cara, qty=2)  # subtotal 4000

    # percent: cart shows the discount; the order records the breakdown with it
    applied = client.post("/api/cart/coupon", json={"code": "ten"}, headers=cara)
    assert applied.status_code == 200
    assert applied.json()["coupon_code"] == "TEN"
    assert applied.json()["discount_cents"] == 400

    order = client.post("/api/checkout", json=checkout_body(), headers=cara).json()
    assert (order["coupon_code"], order["discount_cents"]) == ("TEN", 400)
    # 4000 − 400 + 500 shipping + 400 tax
    assert order["total_cents"] == 4500

    # fixed larger than the subtotal never drives it below zero
    _fill_cart(client, cara, qty=1)  # subtotal 2000
    client.post("/api/cart/coupon", json={"code": "BIG"}, headers=cara)
    order2 = client.post("/api/checkout", json=checkout_body(), headers=cara).json()
    assert order2["discount_cents"] == 2000  # capped at the subtotal
    assert order2["total_cents"] == 0 + 500 + 200  # shipping + tax remain


def test_every_rejection_reason_is_distinct(client) -> None:
    cara = _auth(client)
    _fill_cart(client, cara, qty=1)  # subtotal 2000
    cases = {
        "NOPE": "isn't valid",
        "OFF": "no longer active",
        "LATER": "isn't active yet",
        "PAST": "expired",
        "MIN50": "minimum",
        "GONE": "fully redeemed",
    }
    for code, needle in cases.items():
        resp = client.post("/api/cart/coupon", json={"code": code}, headers=cara)
        assert resp.status_code == 422, code
        assert needle in resp.json()["errors"]["coupon"][0], code


def test_checkout_revalidates_and_per_customer_limit_holds(client) -> None:
    cara = _auth(client)
    boss = _auth(client, "admin@example.com", "secret-admin")

    # apply, then the admin deactivates it before checkout → placement 422s, nothing created
    _fill_cart(client, cara)
    client.post("/api/cart/coupon", json={"code": "TEN"}, headers=cara)
    coupon_id = next(
        c["id"]
        for c in client.get("/api/admin/coupons", headers=boss).json()
        if c["code"] == "TEN"
    )
    client.patch(
        f"/api/admin/coupons/{coupon_id}", json={"active": False}, headers=boss
    )
    rejected = client.post("/api/checkout", json=checkout_body(), headers=cara)
    assert rejected.status_code == 422
    assert client.get("/api/orders", headers=cara).json() == []

    # per-customer limit: first use OK, second 422
    client.delete("/api/cart/coupon", headers=cara)
    client.post("/api/cart/coupon", json={"code": "ONCE"}, headers=cara)
    assert (
        client.post("/api/checkout", json=checkout_body(), headers=cara).status_code
        == 201
    )
    _fill_cart(client, cara)
    client.post("/api/cart/coupon", json={"code": "ONCE"}, headers=cara)
    again = client.post("/api/checkout", json=checkout_body(), headers=cara)
    assert again.status_code == 422
    assert "maximum" in again.json()["errors"]["coupon"][0]


def test_remove_restores_and_merge_drops_the_guest_coupon(client) -> None:
    cara = _auth(client)
    _fill_cart(client, cara)
    client.post("/api/cart/coupon", json={"code": "TEN"}, headers=cara)
    removed = client.delete("/api/cart/coupon", headers=cara)
    assert removed.json()["coupon_code"] is None
    assert removed.json()["discount_cents"] == 0

    # a guest cart with a coupon merges into the user's cart: the USER cart's (absent) coupon
    # wins — the guest code is deterministically dropped
    guest_token = client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}
    ).json()["cart_token"]
    client.post(
        "/api/cart/coupon",
        json={"code": "FIVER"},
        headers={"X-Cart-Token": guest_token},
    )
    merged = _auth(client)  # login WITHOUT the token header — no merge
    client.post(
        "/api/login",
        json={"email": "cara@example.com", "password": "secret-cara"},
        headers={"X-Cart-Token": guest_token},
    )
    cart = client.get("/api/cart", headers=merged).json()
    assert cart["coupon_code"] is None  # the guest's code did not graft on


def test_admin_coupon_crud_and_authz(client) -> None:
    boss = _auth(client, "admin@example.com", "secret-admin")
    support = _auth(client, "support@example.com", "secret-support")

    created = client.post(
        "/api/admin/coupons",
        json={"code": "spring25", "type": "percent", "value": 25},
        headers=boss,
    )
    assert created.status_code == 201
    assert created.json()["code"] == "SPRING25"  # normalized

    # duplicates + bad values are 422s
    assert (
        client.post(
            "/api/admin/coupons",
            json={"code": "SPRING25", "type": "percent", "value": 25},
            headers=boss,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/admin/coupons",
            json={"code": "P200", "type": "percent", "value": 200},
            headers=boss,
        ).status_code
        == 422
    )

    # support can READ but not mutate
    assert client.get("/api/admin/coupons", headers=support).status_code == 200
    assert (
        client.post(
            "/api/admin/coupons",
            json={"code": "X", "type": "fixed", "value": 100},
            headers=support,
        ).status_code
        == 403
    )
