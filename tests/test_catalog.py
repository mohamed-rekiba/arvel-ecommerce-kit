"""Catalog read API — exercised through the real served HTTP path (litestar TestClient over the
app built by the production bootstrap). Seeds a deterministic catalog into a temp sqlite file the
served app reads, then asserts search, filtering, pagination shape, eager-loading, and 404s.
"""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'catalog.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def migrate_and_seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (Category, Product, ProductVariant):
            model.set_connection(db)
        shirts = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        await Category.create(
            translations={"en": {"name": "Shoes"}}, slug="shoes", published=True
        )  # empty → still hidden
        # 25 active "Aero" products (to test pagination) + 1 draft (to test the status filter)
        for i in range(25):
            p = await Product.create(
                category_id=shirts.id,
                translations={
                    "en": {
                        "name": f"Aero Shirt {i:02d}",
                        "description": "A breathable shirt.",
                    }
                },
                slug=f"aero-shirt-{i:02d}",
                price_cents=1999 + i,
                currency="USD",
                status=ProductStatus.ACTIVE,
                published=True,  # retrievable (published, category published, no vendor = first-party)
            )
            await ProductVariant.create(
                product_id=p.id, sku=f"AERO-{i:02d}-S", name="Small", stock=10
            )
        await Product.create(
            category_id=shirts.id,
            translations={
                "en": {"name": "Secret Draft Shirt", "description": "not public yet"}
            },
            slug="secret-draft",
            price_cents=5000,
            currency="USD",
            status=ProductStatus.DRAFT,
            published=False,  # not retrievable → hidden from the storefront
        )
        for model in (Category, Product, ProductVariant):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(migrate_and_seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def test_categories_index(client) -> None:
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    names = [c["translation"]["name"] for c in resp.json()]
    assert names == ["Shirts"]  # Shoes is empty (no retrievable products) → hidden


def test_products_index_paginates_active_only(client) -> None:
    resp = client.get("/api/products")
    assert resp.status_code == 200
    body = resp.json()
    # Laravel length-aware paginator JSON shape
    assert body["per_page"] == 15
    assert body["current_page"] == 1
    assert body["total"] == 25  # 25 retrievable; the unpublished draft is excluded
    assert len(body["data"]) == 15
    # eager-loaded relations are present on each row
    first = body["data"][0]
    assert first["category"]["slug"] == "shirts"
    assert isinstance(first["variants"], list) and first["variants"][0][
        "sku"
    ].startswith("AERO-")


def test_products_index_second_page(client) -> None:
    body = client.get("/api/products?page=2").json()
    assert body["current_page"] == 2
    assert len(body["data"]) == 10  # 25 active - 15 on page 1


def test_products_search_filters_by_name(client) -> None:
    body = client.get("/api/products?q=Aero Shirt 07").json()
    assert body["total"] == 1
    assert body["data"][0]["slug"] == "aero-shirt-07"


def test_unpublished_product_is_hidden_from_the_storefront(client) -> None:
    # the draft never appears in the list, and its detail page 404s (not public)
    body = client.get("/api/products").json()
    assert "secret-draft" not in {p["slug"] for p in body["data"]}
    assert client.get("/api/products/secret-draft").status_code == 404


def test_product_show_eager_loads_and_404s(client) -> None:
    ok = client.get("/api/products/aero-shirt-03")
    assert ok.status_code == 200
    product = ok.json()
    assert product["slug"] == "aero-shirt-03"
    assert product["status"] == "active"  # enum cast serializes to its string value
    assert product["category"]["translation"]["name"] == "Shirts"
    assert product["variants"][0]["stock"] == 10

    missing = client.get("/api/products/does-not-exist")
    assert missing.status_code == 404
