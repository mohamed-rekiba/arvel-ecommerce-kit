"""Module C — retrievability through the served storefront (on sqlite, where the materialized views
degrade to live plain views). Builds a mixed tree and asserts the recursive-CTE rules: a product is
hidden when an ancestor category is unpublished, when its vendor is unpublished, when it is itself
unpublished; a category is hidden when empty or under an unpublished ancestor."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.models.category import Category
from app.models.product import Product
from app.models.vendor import Vendor


@pytest.fixture
def client(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    url = f"sqlite+aiosqlite:///{tmp_path / 'retr.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (Vendor, Category, Product):
            model.set_connection(db)
        acme = await Vendor.create(name="Acme", slug="acme", published=True)
        shady = await Vendor.create(name="Shady", slug="shady", published=False)
        root = await Category.create(
            translations={"en": {"name": "Root"}}, slug="root", published=True
        )
        phones = await Category.create(
            translations={"en": {"name": "Phones"}},
            slug="phones",
            parent_id=root.id,
            published=True,
        )
        await Category.create(
            translations={"en": {"name": "Empty"}},
            slug="empty",
            parent_id=root.id,
            published=True,
        )
        hidden_root = await Category.create(
            translations={"en": {"name": "HiddenRoot"}}, slug="hroot", published=False
        )
        hidden_child = await Category.create(
            translations={"en": {"name": "HiddenChild"}},
            slug="hchild",
            parent_id=hidden_root.id,
            published=True,
        )

        async def product(slug, category_id, vendor_id, published) -> None:  # type: ignore[no-untyped-def]
            await Product.create(
                translations={"en": {"name": slug, "description": "d"}},
                slug=slug,
                category_id=category_id,
                vendor_id=vendor_id,
                price_cents=1000,
                currency="USD",
                status="active" if published else "draft",
                published=published,
            )

        await product("good", phones.id, acme.id, True)  # retrievable
        await product(
            "under-hidden-ancestor", hidden_child.id, acme.id, True
        )  # hidden: ancestor unpublished
        await product(
            "shady-vendor", phones.id, shady.id, True
        )  # hidden: vendor unpublished
        await product("draft", phones.id, acme.id, False)  # hidden: unpublished
        for model in (Vendor, Category, Product):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def test_only_retrievable_products_are_listed(client) -> None:  # type: ignore[no-untyped-def]
    slugs = {p["slug"] for p in client.get("/api/products").json()["data"]}
    assert slugs == {"good"}  # the other three are each hidden by a different rule


def test_hidden_products_404_individually(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/products/good").status_code == 200
    for slug in ("under-hidden-ancestor", "shady-vendor", "draft"):
        assert client.get(f"/api/products/{slug}").status_code == 404


def test_only_retrievable_categories_are_listed(client) -> None:  # type: ignore[no-untyped-def]
    slugs = {c["slug"] for c in client.get("/api/categories").json()}
    assert slugs == {"root", "phones"}  # empty + hidden branch excluded
