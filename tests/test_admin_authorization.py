"""Admin authorization — the Gate/ProductPolicy guards catalog mutation through the real served
path. A customer is denied (403 on create, 404 on update/delete via deny_as_not_found); an admin
is allowed. Exercises arvel policies, user.can, AuthorizationError → HTTP status, and middleware.
"""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from tests.rbac_helpers import seed_rbac


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'authz.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def migrate_and_seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product):
            model.set_connection(db)
        await seed_rbac(db)
        admin = await User.create(
            name="Admin",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await admin.assign_role(
            "super-admin"
        )  # RBAC: catalog authority (bypasses via Gate.before)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts"
        )
        await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Existing"}},
            slug="existing",
            price_cents=1000,
            currency="USD",
            status="active",
        )
        for model in (User, Category, Product):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(migrate_and_seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _token(client, email, password):
    return client.post(
        "/api/login", json={"email": email, "password": password}
    ).json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_is_rejected(client) -> None:
    # a guest is always rejected — even a malformed body may 400 first (validation precedes auth middleware)
    resp = client.post(
        "/api/admin/products",
        json={
            "category_id": 1,
            "price_cents": 100,
            "translations": {"en": {"name": "X"}},
        },
    )
    assert resp.status_code == 401


def test_customer_cannot_mutate_catalog(client) -> None:
    token = _token(client, "cara@example.com", "secret-cara")
    create = client.post(
        "/api/admin/products",
        json={
            "category_id": 1,
            "price_cents": 100,
            "translations": {"en": {"name": "Hacky"}},
        },
        headers=_auth(token),
    )
    assert create.status_code == 403  # policy.create → deny() → 403
    # update/delete deny AS 404 (deny_as_not_found) — existence not leaked
    assert (
        client.put(
            "/api/admin/products/1",
            json={"translations": {"en": {"name": "x"}}},
            headers=_auth(token),
        ).status_code
        == 404
    )
    assert (
        client.delete("/api/admin/products/1", headers=_auth(token)).status_code == 404
    )


def test_admin_can_mutate_catalog(client) -> None:
    token = _token(client, "admin@example.com", "secret-admin")
    create = client.post(
        "/api/admin/products",
        json={
            "category_id": 1,
            "price_cents": 2500,
            "translations": {"en": {"name": "Admin Tee"}},
        },
        headers=_auth(token),
    )
    assert create.status_code == 201
    new_id = create.json()["id"]

    upd = client.put(
        f"/api/admin/products/{new_id}",
        json={"translations": {"en": {"name": "Admin Tee v2"}}, "status": "active"},
        headers=_auth(token),
    )
    assert upd.status_code == 200
    assert upd.json()["translations"][0]["name"] == "Admin Tee v2"
    assert upd.json()["status"] == "active"

    assert (
        client.delete(f"/api/admin/products/{new_id}", headers=_auth(token)).status_code
        == 200
    )


def test_admin_create_validates(client) -> None:
    token = _token(client, "admin@example.com", "secret-admin")
    bad = client.post(
        "/api/admin/products",
        json={
            "category_id": 1,
            "price_cents": -5,
            "translations": {"en": {"name": ""}},
        },
        headers=_auth(token),
    )
    assert bad.status_code == 422


def test_admin_lists_all_products_with_is_visible(client) -> None:
    token = _token(client, "admin@example.com", "secret-admin")
    body = client.get("/api/admin/products", headers=_auth(token)).json()
    assert (
        body["total"] == 1
    )  # admin sees the product even though it's hidden from the storefront
    product = body["data"][0]
    assert product["slug"] == "existing"
    assert product["is_visible"] is False  # not published → not retrievable
    assert product["published"] is False


def test_admin_lists_all_categories_with_is_visible(client) -> None:
    token = _token(client, "admin@example.com", "secret-admin")
    body = client.get("/api/admin/categories", headers=_auth(token)).json()
    assert {c["slug"] for c in body["data"]} == {"shirts"}
    assert all("is_visible" in c for c in body["data"])


def test_customer_cannot_list_admin_products(client) -> None:
    token = _token(client, "cara@example.com", "secret-cara")
    assert client.get("/api/admin/products", headers=_auth(token)).status_code == 403
