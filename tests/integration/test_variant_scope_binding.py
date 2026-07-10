"""K4 — the E6 scope guarantee on real Postgres: a variant nested under the WRONG product 404s
because the route's ``.scope_bindings()`` constrains the lookup, not because a controller
re-derives the parent and checks it. The controller performs no such re-check any more (K4 deleted
it) — so if the scope ever silently fell back to a global lookup (the fail-open footgun DR-0053
flags), this test would see a 200 that wrongly mutated another product's variant, not a 404.
"""

from __future__ import annotations

import asyncio

import pytest

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from tests.rbac_helpers import seed_rbac

pytestmark = pytest.mark.integration

_MODELS = (User, Category, Product, ProductVariant)


async def _seed_two_products(url: str) -> dict[str, int]:
    """Two products, each with its own variant — the minimal shape that can distinguish a
    same-parent resolve from a cross-parent 404."""
    db = ConnectionResolver({"default": {"url": url}})
    migrator = Migrator(db)
    await (
        migrator.drop_all()
    )  # the PG container is session-scoped; each test starts clean
    await migrator.run(discover_migrations(["database/migrations"]))
    await seed_rbac(db)
    for model in _MODELS:
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
        product_a = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee A"}},
            slug="tee-a",
            price_cents=1000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        product_b = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee B"}},
            slug="tee-b",
            price_cents=1500,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        variant_a = await ProductVariant.create(
            product_id=product_a.id,
            sku="A-S",
            name="S",
            price_adjustment_cents=0,
            stock=5,
        )
        variant_b = await ProductVariant.create(
            product_id=product_b.id,
            sku="B-S",
            name="S",
            price_adjustment_cents=0,
            stock=5,
        )
        return {
            "product_a": product_a.id,
            "product_b": product_b.id,
            "variant_a": variant_a.id,
            "variant_b": variant_b.id,
        }
    finally:
        for model in _MODELS:
            model.set_connection(None)
        await db.dispose()


def test_cross_parent_variant_id_404s_via_the_scope_not_the_controller(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = asyncio.run(_seed_two_products(postgres_url))
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from litestar.testing import TestClient

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as client:
        admin = {
            "Authorization": f"Bearer {client.post('/api/login', json={'email': 'admin@example.com', 'password': 'secret-admin'}).json()['token']}"
        }

        # same-parent: both real pairs resolve (200) — proves the happy path still works nested.
        same_a = client.patch(
            f"/api/admin/products/{ids['product_a']}/variants/{ids['variant_a']}",
            json={"name": "Small"},
            headers=admin,
        )
        assert same_a.status_code == 200, same_a.text
        same_b = client.patch(
            f"/api/admin/products/{ids['product_b']}/variants/{ids['variant_b']}",
            json={"name": "Small"},
            headers=admin,
        )
        assert same_b.status_code == 200, same_b.text

        # cross-parent: variant_a EXISTS (just proved above) and belongs to product_a — requesting
        # it nested under product_b must 404. The controller no longer re-derives or checks the
        # parent itself (K4 deleted that code), so this 404 can only be the scoped binding at work.
        cross = client.patch(
            f"/api/admin/products/{ids['product_b']}/variants/{ids['variant_a']}",
            json={"name": "Hijacked"},
            headers=admin,
        )
        assert cross.status_code == 404, cross.text

        # the delete + stock-adjust siblings share the same scoped route shape — same guarantee.
        cross_stock = client.post(
            f"/api/admin/products/{ids['product_b']}/variants/{ids['variant_a']}/stock",
            json={"set": 99},
            headers=admin,
        )
        assert cross_stock.status_code == 404, cross_stock.text
        cross_delete = client.delete(
            f"/api/admin/products/{ids['product_b']}/variants/{ids['variant_a']}",
            headers=admin,
        )
        assert cross_delete.status_code == 404, cross_delete.text

        # a variant id that doesn't exist anywhere still 404s (binding miss, never a 500).
        missing = client.patch(
            f"/api/admin/products/{ids['product_a']}/variants/999999",
            json={"name": "Ghost"},
            headers=admin,
        )
        assert missing.status_code == 404, missing.text

        # proof the cross-parent 404 was never about existence: variant_a is still there,
        # unmutated by the rejected "Hijacked" request, and still resolves under its real parent.
        still_a = client.get(
            f"/api/admin/products/{ids['product_a']}/variants", headers=admin
        )
        assert still_a.status_code == 200
        names = {v["name"] for v in still_a.json()}
        assert "Hijacked" not in names and "Small" in names
