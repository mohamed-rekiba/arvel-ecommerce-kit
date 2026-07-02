"""S16 — reviews through the served path: purchase eligibility, moderation lifecycle, the
denormalized aggregate, morph relations, and every edge from the story."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from tests.checkout_helpers import checkout_body
from tests.rbac_helpers import seed_rbac


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'reviews.sqlite'}"
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
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _auth(client, email, password):
    token = client.post(
        "/api/login", json={"email": email, "password": password}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_review_lifecycle_and_aggregate(client) -> None:
    cara = _auth(client, "cara@example.com", "secret-cara")
    support = _auth(client, "support@example.com", "secret-support")

    # no purchase yet → 403 with a clear reason
    denied = client.post(
        "/api/products/tee/reviews", json={"rating": 5, "body": "Nice"}, headers=cara
    )
    assert denied.status_code == 403

    # buy it (PENDING order isn't enough — pay it first)
    client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}, headers=cara
    )
    order = client.post("/api/checkout", json=checkout_body(), headers=cara).json()
    still_denied = client.post(
        "/api/products/tee/reviews", json={"rating": 5, "body": "Nice"}, headers=cara
    )
    assert still_denied.status_code == 403  # pending ≠ purchased

    # pay via the gateway webhook path is heavy here; the state machine is the boundary — use
    # the dev-gateway-free route: order token + pay is mocked elsewhere. Mark paid via checkout's
    # admin transition using a super-admin seeded through RBAC helper? Simplest: register a
    # dedicated admin through the API is impossible — so run the transition through the ORM within
    # the app portal (the admin endpoint path is already covered by checkout tests).
    async def _mark_paid() -> None:
        from app.enums import OrderStatus
        from app.models.order import Order

        row = await Order.find_or_fail(order["id"])
        row.status = OrderStatus.PAID
        await row.save()

    with client.portal() as portal:
        portal.call(_mark_paid)

        # rating bounds + empty body are 422s
        assert (
            client.post(
                "/api/products/tee/reviews",
                json={"rating": 6, "body": "x"},
                headers=cara,
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/products/tee/reviews",
                json={"rating": 4, "body": "  "},
                headers=cara,
            ).status_code
            == 422
        )

        # submit → PENDING: invisible publicly, visible to the author as 'mine'
        created = client.post(
            "/api/products/tee/reviews",
            json={"rating": 4, "body": "Solid tee.", "title": "Good"},
            headers=cara,
        )
        assert created.status_code == 201
        listing = client.get("/api/products/tee/reviews", headers=cara).json()
        assert listing["reviews"] == [] and listing["mine"]["status"] == "pending"
        assert client.get("/api/products/tee").json()["rating_count"] == 0

        # duplicate → 422
        assert (
            client.post(
                "/api/products/tee/reviews",
                json={"rating": 5, "body": "again"},
                headers=cara,
            ).status_code
            == 422
        )

        # support approves → public + aggregate updates everywhere
        review_id = listing["mine"]["id"]
        approved = client.post(
            f"/api/admin/reviews/{review_id}/approve", headers=support
        )
        assert approved.status_code == 200
        listing = client.get("/api/products/tee/reviews").json()
        assert [r["rating"] for r in listing["reviews"]] == [4]
        assert listing["rating_avg"] == 4.0 and listing["rating_count"] == 1
        pdp = client.get("/api/products/tee").json()
        assert (pdp["rating_avg"], pdp["rating_count"]) == (4.0, 1)

        # reject AFTER approval subtracts from the aggregate (never negative)
        client.post(f"/api/admin/reviews/{review_id}/reject", headers=support)
        pdp = client.get("/api/products/tee").json()
        assert (pdp["rating_avg"], pdp["rating_count"]) == (None, 0)
        # the author still sees their own (now rejected) review
        mine = client.get("/api/products/tee/reviews", headers=cara).json()["mine"]
        assert mine["status"] == "rejected"


def test_moderation_requires_the_permission(client) -> None:
    cara = _auth(client, "cara@example.com", "secret-cara")
    assert client.get("/api/admin/reviews", headers=cara).status_code == 403
    assert client.post("/api/admin/reviews/1/approve", headers=cara).status_code == 403
    assert client.get("/api/admin/reviews").status_code == 401
    # unknown status filter is a clean 422
    support = _auth(client, "support@example.com", "secret-support")
    assert (
        client.get("/api/admin/reviews?status=weird", headers=support).status_code
        == 422
    )
