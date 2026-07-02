"""v6 storefront features through the served path: the featured rail (admin toggle → catalog
filter), catalog price-range filters, and the announcement bar (newest live announce-flagged
coupon; silent 404 when nothing is announced)."""

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
from tests.rbac_helpers import seed_rbac


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'features.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        models = (User, Category, Product, ProductVariant, Coupon)
        for model in models:
            model.set_connection(db)
        admin = await User.create(
            name="Ada",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("super-admin")
        cat = await Category.create(
            translations={"en": {"name": "Gear"}}, slug="gear", published=True
        )
        for slug, price, featured in (
            ("cheap", 500, False),
            ("mid", 2500, True),
            ("dear", 9000, False),
        ):
            p = await Product.create(
                category_id=cat.id,
                translations={"en": {"name": slug.title()}},
                slug=slug,
                price_cents=price,
                currency="USD",
                status=ProductStatus.ACTIVE,
                published=True,
                featured=featured,
            )
            await ProductVariant.create(
                product_id=p.id, sku=f"{slug}-1", name="One", price_adjustment_cents=0, stock=5
            )
        for model in models:
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _admin(client):
    token = client.post(
        "/api/login", json={"email": "admin@example.com", "password": "secret-admin"}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_featured_filter_and_admin_toggle(client) -> None:
    slugs = {p["slug"] for p in client.get("/api/products?featured=true").json()["data"]}
    assert slugs == {"mid"}
    # the listing payload carries the flag (the storefront rail + admin column need it)
    assert client.get("/api/products/mid").json()["featured"] is True

    # the admin flips it off; the rail follows
    admin = _admin(client)
    updated = client.put("/api/admin/products/2", json={"featured": False}, headers=admin)
    assert updated.status_code == 200, updated.text
    assert updated.json()["featured"] is False
    assert client.get("/api/products?featured=true").json()["data"] == []


def test_price_range_filters(client) -> None:
    assert {
        p["slug"] for p in client.get("/api/products?min_price=1000").json()["data"]
    } == {"mid", "dear"}
    assert {
        p["slug"] for p in client.get("/api/products?max_price=3000").json()["data"]
    } == {"cheap", "mid"}
    assert {
        p["slug"]
        for p in client.get("/api/products?min_price=1000&max_price=3000").json()["data"]
    } == {"mid"}


def test_announcement_surfaces_the_newest_live_flagged_coupon(client) -> None:
    # nothing announced yet → the storefront hides the bar
    assert client.get("/api/announcement").status_code == 404

    admin = _admin(client)
    client.post(
        "/api/admin/coupons",
        json={"code": "OLD5", "type": "percent", "value": 5, "announce": True},
        headers=admin,
    )
    created = client.post(
        "/api/admin/coupons",
        json={"code": "SAVE10", "type": "percent", "value": 10, "announce": True},
        headers=admin,
    )
    assert created.json()["announce"] is True

    body = client.get("/api/announcement").json()
    assert body["code"] == "SAVE10"  # newest wins
    assert body["type"] == "percent" and body["value"] == 10

    # un-flagging (or deactivating) pulls it off the bar
    client.patch(
        f"/api/admin/coupons/{created.json()['id']}",
        json={"announce": False},
        headers=admin,
    )
    assert client.get("/api/announcement").json()["code"] == "OLD5"


def test_expired_announcement_is_skipped(client) -> None:
    async def _seed_expired() -> None:
        await Coupon.create(
            code="GONE",
            type=CouponType.PERCENT,
            value=20,
            uses=0,
            active=True,
            announce=True,
            ends_at=Date.now().subtract(days=1),
        )

    with client.portal() as portal:
        portal.call(_seed_expired)
    assert client.get("/api/announcement").status_code == 404
