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


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'authz.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def migrate_and_seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product):
            model.set_connection(db)
        await User.create(name="Admin", email="admin@example.com", password="secret-admin",
                          role=UserRole.ADMIN)
        await User.create(name="Cara", email="cara@example.com", password="secret-cara",
                          role=UserRole.CUSTOMER)
        cat = await Category.create(name="Shirts", slug="shirts")
        await Product.create(category_id=cat.id, name="Existing", slug="existing",
                             price_cents=1000, currency="USD", status="active")
        for model in (User, Category, Product):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(migrate_and_seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _token(client, email, password):
    return client.post("/api/login", json={"email": email, "password": password}).json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_is_rejected(client) -> None:
    # a guest with an otherwise-valid body is rejected by the Authenticate middleware (401).
    # (A guest with a malformed body may surface 400 first — body validation precedes route
    # middleware in litestar — but a guest can never succeed, which is the security property.)
    resp = client.post(
        "/api/admin/products", json={"category_id": 1, "name": "X", "price_cents": 100}
    )
    assert resp.status_code == 401


def test_customer_cannot_mutate_catalog(client) -> None:
    token = _token(client, "cara@example.com", "secret-cara")
    create = client.post(
        "/api/admin/products",
        json={"category_id": 1, "name": "Hacky", "price_cents": 100},
        headers=_auth(token),
    )
    assert create.status_code == 403  # policy.create → deny() → 403
    # update/delete deny AS 404 (deny_as_not_found) — existence not leaked
    assert client.put("/api/admin/products/1", json={"name": "x"}, headers=_auth(token)).status_code == 404
    assert client.delete("/api/admin/products/1", headers=_auth(token)).status_code == 404


def test_admin_can_mutate_catalog(client) -> None:
    token = _token(client, "admin@example.com", "secret-admin")
    create = client.post(
        "/api/admin/products",
        json={"category_id": 1, "name": "Admin Tee", "price_cents": 2500},
        headers=_auth(token),
    )
    assert create.status_code == 201
    new_id = create.json()["id"]

    upd = client.put(
        f"/api/admin/products/{new_id}",
        json={"name": "Admin Tee v2", "status": "active"},
        headers=_auth(token),
    )
    assert upd.status_code == 200
    assert upd.json()["name"] == "Admin Tee v2"
    assert upd.json()["status"] == "active"

    assert client.delete(f"/api/admin/products/{new_id}", headers=_auth(token)).status_code == 200


def test_admin_create_validates(client) -> None:
    token = _token(client, "admin@example.com", "secret-admin")
    bad = client.post(
        "/api/admin/products",
        json={"category_id": 1, "name": "", "price_cents": -5},
        headers=_auth(token),
    )
    assert bad.status_code == 422
