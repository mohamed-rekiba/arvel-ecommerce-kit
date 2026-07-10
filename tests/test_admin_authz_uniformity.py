"""DR-0055 regression: an authenticated-but-unauthorized caller must get the SAME status for an
existing bound id as for a nonexistent one. K4's route-model binding resolves existence before a
handler runs; a class-level permission check that used to run first (and is now Authorize route
middleware, per DR-0055) must keep denying uniformly — otherwise a logged-in customer can use the
403-vs-404 split as a zero-extra-credential existence oracle (order-id enumeration being the
sharpest case). Covers one Authorize-middleware route per K4 conversion class (an order, a banner)
plus the per-object deny-as-404 case (product update), which was already uniform before this DR
and must stay that way.
"""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.banner import Banner
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from tests.checkout_helpers import checkout_body
from tests.rbac_helpers import seed_rbac

_NONEXISTENT = 999999


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'authz_uniformity.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        for model in (User, Category, Product, ProductVariant, Banner):
            model.set_connection(db)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,  # authenticated, but no admin permission whatsoever
        )
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        product = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee"}},
            slug="tee",
            price_cents=2000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        await ProductVariant.create(
            product_id=product.id,
            sku="TEE-S",
            name="S",
            price_adjustment_cents=0,
            stock=5,
        )
        await Banner.create(
            translations={"en": {"title": "Sale"}},
            cta_to="/catalog",
            sort=0,
            active=True,
        )
        for model in (User, Category, Product, ProductVariant, Banner):
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


def test_authorize_middleware_route_denies_uniformly(client) -> None:
    """orders.view (Authorize middleware, DR-0055): an unauthorized customer gets the SAME status
    for a real order as for one that doesn't exist — the permission gate, not existence, decides."""
    customer = _auth(client, "cara@example.com", "secret-cara")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=customer,
    )
    order = client.post("/api/checkout", json=checkout_body(), headers=customer).json()

    existing = client.get(f"/api/admin/orders/{order['id']}", headers=customer)
    missing = client.get(f"/api/admin/orders/{_NONEXISTENT}", headers=customer)
    assert existing.status_code == missing.status_code == 403, (
        existing.status_code,
        missing.status_code,
    )


def test_authorize_middleware_route_denies_uniformly_for_banners(client) -> None:
    """catalog.update on a banner mutation (Authorize middleware, DR-0055) — same uniformity
    guarantee on a second, independent resource family."""
    customer = _auth(client, "cara@example.com", "secret-cara")

    existing = client.patch(
        "/api/admin/banners/1", json={"active": False}, headers=customer
    )
    missing = client.patch(
        f"/api/admin/banners/{_NONEXISTENT}", json={"active": False}, headers=customer
    )
    assert existing.status_code == missing.status_code == 403, (
        existing.status_code,
        missing.status_code,
    )


def test_per_object_policy_route_was_already_uniform(client) -> None:
    """PUT /admin/products/{id}: authorization needs the bound instance (deny_as_not_found), so it
    stays in-handler per DR-0055's exception clause — already uniform (both 404) before this DR,
    confirmed unchanged by it."""
    customer = _auth(client, "cara@example.com", "secret-cara")

    existing = client.put(
        "/api/admin/products/1",
        json={"translations": {"en": {"name": "Hacked"}}},
        headers=customer,
    )
    missing = client.put(
        f"/api/admin/products/{_NONEXISTENT}",
        json={"translations": {"en": {"name": "Hacked"}}},
        headers=customer,
    )
    assert existing.status_code == missing.status_code == 404, (
        existing.status_code,
        missing.status_code,
    )
