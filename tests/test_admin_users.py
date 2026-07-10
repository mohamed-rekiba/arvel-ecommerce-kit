"""S13 — admin user directory through the served path: search + pagination, detail with roles and
order summary, role assign/revoke effects, the authz matrix, and the privacy guard (no secrets in
any response)."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.shipping_method import ShippingMethod
from app.models.user import User
from tests.checkout_helpers import checkout_body
from tests.rbac_helpers import seed_rbac


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'users.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        for model in (User, Category, Product, ProductVariant, ShippingMethod):
            model.set_connection(db)
        _verified_customer = await User.create(
            name="Cara Lund",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        await _verified_customer.mark_email_as_verified()
        support = await User.create(
            name="Sup",
            email="support@example.com",
            password="secret-support",
            role=UserRole.ADMIN,
        )
        await support.assign_role("support")
        catalog = await User.create(
            name="Cat",
            email="catalog@example.com",
            password="secret-catalog",
            role=UserRole.ADMIN,
        )
        await catalog.assign_role("catalog-manager")
        boss = await User.create(
            name="Boss",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await boss.assign_role("super-admin")
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
            product_id=p.id, sku="TEE-S", name="S", price_adjustment_cents=0, stock=50
        )
        await ShippingMethod.create(
            code="standard", name="Standard", rate_cents=500, active=True, sort=0
        )
        for model in (User, Category, Product, ProductVariant, ShippingMethod):
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


def test_directory_search_detail_and_privacy(client) -> None:
    support = _auth(client, "support@example.com", "secret-support")

    # Cara places an order so the detail has a summary
    cara = _auth(client, "cara@example.com", "secret-cara")
    client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 2}, headers=cara
    )
    client.post("/api/checkout", json=checkout_body(), headers=cara)

    # search finds her; an unknown email yields a clean empty page
    page = client.get("/api/admin/users?q=cara", headers=support).json()
    assert [u["email"] for u in page["data"]] == ["cara@example.com"]
    assert client.get("/api/admin/users?q=ghost", headers=support).json()["data"] == []

    # detail: profile, roles, order summary — and NOTHING secret-shaped
    detail = client.get(f"/api/admin/users/{page['data'][0]['id']}", headers=support)
    body = detail.json()
    assert body["orders_count"] == 1 and body["total_spent_cents"] == 4900
    assert body["roles"] == []
    forbidden = {"password", "token", "remember", "reset"}
    assert not (set(map(str.lower, body.keys())) & forbidden)

    # unknown id → 404, not a 500
    assert client.get("/api/admin/users/999", headers=support).status_code == 404


def test_role_changes_take_effect(client) -> None:
    """Assign via the existing roles.manage endpoint; the directory reflects it and the
    permission effect is real (a revoked catalog-manager loses product mutation)."""
    boss = _auth(client, "admin@example.com", "secret-admin")
    cara_id = client.get("/api/admin/users?q=cara", headers=boss).json()["data"][0][
        "id"
    ]

    # assign catalog-manager to Cara → she can create products
    client.post(
        f"/api/admin/users/{cara_id}/roles",
        json={"role": "catalog-manager"},
        headers=boss,
    )
    assert (
        "catalog-manager"
        in client.get(f"/api/admin/users/{cara_id}", headers=boss).json()["roles"]
    )
    cara = _auth(client, "cara@example.com", "secret-cara")
    ok = client.post(
        "/api/admin/products",
        json={
            "category_id": 1,
            "price_cents": 500,
            "translations": {"en": {"name": "New"}},
        },
        headers=cara,
    )
    assert ok.status_code == 201

    # revoke → she loses it
    client.delete(f"/api/admin/users/{cara_id}/roles/catalog-manager", headers=boss)
    denied = client.post(
        "/api/admin/products",
        json={
            "category_id": 1,
            "price_cents": 500,
            "translations": {"en": {"name": "Nope"}},
        },
        headers=cara,
    )
    assert denied.status_code == 403


def test_directory_authz_matrix(client) -> None:
    # catalog-manager CANNOT browse users; guests 401
    catalog = _auth(client, "catalog@example.com", "secret-catalog")
    assert client.get("/api/admin/users", headers=catalog).status_code == 403
    assert client.get("/api/admin/users/1", headers=catalog).status_code == 403
    assert client.get("/api/admin/users").status_code == 401
