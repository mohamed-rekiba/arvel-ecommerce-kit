"""S11 — admin category + vendor CRUD through the served path: per-locale categories, integrity
guards, vendor publish gating, and the authz deny model."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.models.vendor import Vendor
from tests.rbac_helpers import seed_rbac


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'taxonomy.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        for model in (User, Category, Product, ProductVariant, Vendor):
            model.set_connection(db)
        catalog = await User.create(
            name="Cat",
            email="catalog@example.com",
            password="secret-catalog",
            role=UserRole.ADMIN,
        )
        await catalog.assign_role("catalog-manager")
        support = await User.create(
            name="Sup",
            email="support@example.com",
            password="secret-support",
            role=UserRole.ADMIN,
        )
        await support.assign_role("support")
        vendor = await Vendor.create(
            name="Nordic Audio", slug="nordic-audio", published=True
        )
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        p = await Product.create(
            category_id=cat.id,
            vendor_id=vendor.id,
            translations={"en": {"name": "Tee"}},
            slug="tee",
            price_cents=2000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        await ProductVariant.create(
            product_id=p.id, sku="TEE-S", name="S", price_adjustment_cents=0, stock=5
        )
        for model in (User, Category, Product, ProductVariant, Vendor):
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


def test_category_crud_with_locales_and_integrity(client) -> None:
    admin = _auth(client, "catalog@example.com", "secret-catalog")

    created = client.post(
        "/api/admin/categories",
        json={"translations": {"en": {"name": "Hats"}, "fr": {"name": "Chapeaux"}}},
        headers=admin,
    )
    assert created.status_code == 201, created.text
    cat_id = created.json()["id"]
    assert created.json()["slug"] == "hats"

    # dup slug → 422
    dup = client.post(
        "/api/admin/categories",
        json={"translations": {"en": {"name": "Hats"}}},
        headers=admin,
    )
    assert dup.status_code == 422 and "slug" in dup.json()["errors"]

    # update translations + storefront serves fr
    client.put(
        f"/api/admin/categories/{cat_id}",
        json={"translations": {"en": {"name": "Hats"}, "fr": {"name": "Casquettes"}}},
        headers=admin,
    )
    fr = client.get("/api/categories", headers={"Accept-Language": "fr"}).json()
    # the new empty category isn't retrievable yet — check via the admin index instead
    admin_cats = client.get("/api/admin/categories", headers=admin).json()["data"]
    hats = next(c for c in admin_cats if c["id"] == cat_id)
    assert {t["locale"]: t["name"] for t in hats["translations"]}["fr"] == "Casquettes"
    assert isinstance(fr, list)  # the storefront list still serves

    # a category can't parent itself
    self_parent = client.put(
        f"/api/admin/categories/{cat_id}", json={"parent_id": cat_id}, headers=admin
    )
    assert self_parent.status_code == 422

    # deleting a category WITH products → 422; the empty one deletes
    assert client.delete("/api/admin/categories/1", headers=admin).status_code == 422
    assert (
        client.delete(f"/api/admin/categories/{cat_id}", headers=admin).status_code
        == 200
    )


def test_vendor_publish_gates_retrievability(client) -> None:
    admin = _auth(client, "catalog@example.com", "secret-catalog")

    # baseline: the tee is on the storefront
    assert client.get("/api/products/tee").status_code == 200

    # unpublish the vendor → the product leaves the storefront (live views on sqlite)
    flipped = client.put(
        "/api/admin/vendors/1", json={"published": False}, headers=admin
    )
    assert flipped.status_code == 200 and flipped.json()["published"] is False
    assert client.get("/api/products/tee").status_code == 404

    # republish → it returns
    client.put("/api/admin/vendors/1", json={"published": True}, headers=admin)
    assert client.get("/api/products/tee").status_code == 200

    # create + list vendors; dup slug 422
    created = client.post(
        "/api/admin/vendors", json={"name": "Verge Supply"}, headers=admin
    )
    assert created.status_code == 201
    assert (
        client.post(
            "/api/admin/vendors", json={"name": "Verge Supply"}, headers=admin
        ).status_code
        == 422
    )
    names = [v["name"] for v in client.get("/api/admin/vendors", headers=admin).json()]
    assert names == ["Nordic Audio", "Verge Supply"]


def test_taxonomy_denies_non_catalog_roles(client) -> None:
    support = _auth(client, "support@example.com", "secret-support")
    cases = [
        ("POST", "/api/admin/categories", {"translations": {"en": {"name": "X"}}}),
        ("PUT", "/api/admin/categories/1", {"published": False}),
        ("DELETE", "/api/admin/categories/1", None),
        ("POST", "/api/admin/vendors", {"name": "X"}),
        ("PUT", "/api/admin/vendors/1", {"published": False}),
    ]
    for method, path, body in cases:
        assert (
            client.request(method, path, json=body, headers=support).status_code == 403
        )
        assert client.request(method, path, json=body).status_code == 401
    # support is read-only: it CAN list vendors (catalog.view) but never mutate (asserted above)
    assert client.get("/api/admin/vendors", headers=support).status_code == 200
