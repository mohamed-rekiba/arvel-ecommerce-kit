"""DR-0057 Fix 1, the real proof: arvel's resource routes (`/products/{id}`, no `:int`
converter) now coerce the route key at the binding choke point, so `api_resource` show/
update/destroy resolve an int primary key correctly against Postgres — without the kit's
removed `IntRouteKey` mixin (SQLite silently accepted the untyped string; Postgres rejected it
with `operator does not exist: bigint = character varying`, a 500 only this tier could catch).
A garbage id still 404s cleanly, never a driver error.
"""

from __future__ import annotations

import asyncio

import pytest

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from tests.rbac_helpers import seed_rbac

pytestmark = pytest.mark.integration

_MODELS = (Category, Product)


async def _seed(url: str) -> dict[str, int]:
    from app.models.user import User

    db = ConnectionResolver({"default": {"url": url}})
    migrator = Migrator(db)
    await (
        migrator.drop_all()
    )  # the PG container is session-scoped; each test starts clean
    await migrator.run(discover_migrations(["database/migrations"]))
    await seed_rbac(db)
    for model in (*_MODELS, User):
        model.set_connection(db)
    try:
        admin = await User.create(
            name="Ada",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("super-admin")
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
        return {"category": cat.id, "product": product.id}
    finally:
        for model in (*_MODELS, User):
            model.set_connection(None)
        await db.dispose()


def test_int_route_key_resolves_on_postgres_without_the_kit_mixin(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = asyncio.run(_seed(postgres_url))
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from litestar.testing import TestClient

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as client:
        admin = {
            "Authorization": f"Bearer {client.post('/api/login', json={'email': 'admin@example.com', 'password': 'secret-admin'}).json()['token']}"
        }

        # show: a resource route ({product}, no :int converter) resolves the real int id.
        show = client.get(f"/api/admin/products/{ids['product']}", headers=admin)
        assert show.status_code == 200, show.text

        # update: PUT still works (api_resource now owns update fully — DR-0057 fix 2).
        update = client.put(
            f"/api/admin/products/{ids['product']}",
            json={"translations": {"en": {"name": "Updated Tee"}}},
            headers=admin,
        )
        assert update.status_code == 200, update.text
        # PATCH now also resolves on the same route (the second operation Fix 2 unblocked).
        patch = client.patch(
            f"/api/admin/products/{ids['product']}",
            json={"translations": {"en": {"name": "Patched Tee"}}},
            headers=admin,
        )
        assert patch.status_code == 200, patch.text

        # a garbage id 404s cleanly — never the Postgres driver error the mixin used to guard.
        garbage = client.get("/api/admin/products/abc", headers=admin)
        assert garbage.status_code == 404, garbage.text

        # a second resource family (no authorize_resource — Controller.middleware() path) proves
        # the coercion is general, not products-specific. CategoryController has no `show`, so
        # exercise the binding through `update` (PUT) instead.
        cat_update = client.put(
            f"/api/admin/categories/{ids['category']}",
            json={"published": False},
            headers=admin,
        )
        assert cat_update.status_code == 200, cat_update.text
        cat_garbage = client.put(
            "/api/admin/categories/xyz", json={"published": False}, headers=admin
        )
        assert cat_garbage.status_code == 404, cat_garbage.text

        # destroy: int key still resolves for delete too.
        destroy = client.delete(f"/api/admin/products/{ids['product']}", headers=admin)
        assert destroy.status_code == 200, destroy.text
