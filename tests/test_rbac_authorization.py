"""RBAC + audit trail through the real served path. Four back-office roles with different permission
scopes hit the same admin endpoints; the Gate (permissions + super-admin bypass) decides. Role
assignment and catalog mutations are recorded in the activity log (causer + description)."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from tests.rbac_helpers import seed_rbac

ACCOUNTS = {
    "super-admin@example.com": "super-admin",
    "catalog@example.com": "catalog-manager",
    "orders@example.com": "order-manager",
    "support@example.com": "support",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'rbac.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product):
            model.set_connection(db)
        await seed_rbac(db)
        for email, role in ACCOUNTS.items():
            user = await User.create(
                name=role, email=email, password="secret-admin", role="admin"
            )
            await user.assign_role(role)
        await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        for model in (User, Category, Product):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _auth(client, email):
    token = client.post(
        "/api/login", json={"email": email, "password": "secret-admin"}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _create_product(client, headers, name):
    return client.post(
        "/api/admin/products",
        json={"category_id": 1, "name": name, "price_cents": 1500},
        headers=headers,
    )


def test_catalog_manager_can_mutate_catalog_only(client) -> None:
    h = _auth(client, "catalog@example.com")
    assert _create_product(client, h, "CM Tee").status_code == 201  # has catalog.create
    assert (
        client.get("/api/admin/roles", headers=h).status_code == 403
    )  # no roles.manage
    assert client.get("/api/admin/audit", headers=h).status_code == 403  # no audit.view


def test_order_manager_cannot_touch_catalog(client) -> None:
    h = _auth(client, "orders@example.com")
    assert _create_product(client, h, "OM Tee").status_code == 403  # no catalog.create
    assert client.get("/api/admin/roles", headers=h).status_code == 403


def test_support_can_read_audit_but_not_write_catalog(client) -> None:
    h = _auth(client, "support@example.com")
    assert (
        client.get("/api/admin/audit", headers=h).status_code == 200
    )  # has audit.view
    assert _create_product(client, h, "Sup Tee").status_code == 403  # catalog.view only


def test_super_admin_bypasses_everything(client) -> None:
    h = _auth(client, "super-admin@example.com")
    assert _create_product(client, h, "SA Tee").status_code == 201
    assert client.get("/api/admin/roles", headers=h).status_code == 200
    assert client.get("/api/admin/audit", headers=h).status_code == 200


def test_role_assignment_and_catalog_mutation_are_audited(client) -> None:
    admin = _auth(client, "super-admin@example.com")
    # a catalog mutation is recorded
    _create_product(client, admin, "Audited Tee")
    # assign a role via the API — recorded with the causer
    assigned = client.post(
        "/api/admin/users/2/roles", json={"role": "support"}, headers=admin
    )
    assert assigned.status_code == 200
    assert "support" in assigned.json()["roles"]

    log = client.get("/api/admin/audit", headers=admin).json()
    descriptions = [row["description"] for row in log]
    assert "created product" in descriptions
    assert any("assigned role 'support'" == d for d in descriptions)
    # the role assignment carries the acting admin as causer
    assign_row = next(r for r in log if r["description"] == "assigned role 'support'")
    assert assign_row["causer_id"] == 1  # the super-admin user


def test_roles_endpoint_lists_permissions_per_role(client) -> None:
    h = _auth(client, "super-admin@example.com")
    roles = {
        r["name"]: set(r["permissions"])
        for r in client.get("/api/admin/roles", headers=h).json()
    }
    assert roles["catalog-manager"] == {
        "catalog.view",
        "catalog.create",
        "catalog.update",
        "catalog.delete",
    }
    assert roles["order-manager"] == {"orders.view", "orders.update"}
    assert roles["super-admin"] == set()  # bypass; no explicit grants
