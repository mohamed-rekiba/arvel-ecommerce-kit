"""Module D — translatable catalog content through the served API. A product/category name is stored
per-locale (jsonb) and returned in the request's language (LocaleMiddleware reads Accept-Language)."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.models.category import Category
from app.models.product import Product
from app.models.vendor import Vendor


@pytest.fixture
def client(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    url = f"sqlite+aiosqlite:///{tmp_path / 'i18n.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (Vendor, Category, Product):
            model.set_connection(db)
        vendor = await Vendor.create(name="Acme", slug="acme", published=True)
        cat = await Category.create(
            translations={"en": {"name": "Phones"}, "fr": {"name": "Téléphones"}}, slug="phones", published=True
        )
        await Product.create(
            translations={"en": {"name": "Aurora Phone", "description": "d"}, "fr": {"name": "Téléphone Aurora"}},
            slug="aurora",
            category_id=cat.id,
            vendor_id=vendor.id,
            price_cents=1000,
            currency="USD",
            status="active",
            published=True,
        )
        for model in (Vendor, Category, Product):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def test_product_name_follows_accept_language(client) -> None:  # type: ignore[no-untyped-def]
    en = client.get("/api/products").json()["data"][0]
    assert en["translation"]["name"] == "Aurora Phone"
    fr = client.get("/api/products", headers={"Accept-Language": "fr"}).json()["data"][0]
    assert fr["translation"]["name"] == "Téléphone Aurora"


def test_category_name_follows_accept_language(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/categories").json()[0]["translation"]["name"] == "Phones"
    fr = client.get("/api/categories", headers={"Accept-Language": "fr"}).json()
    assert fr[0]["translation"]["name"] == "Téléphones"


def test_search_matches_the_current_locale(client) -> None:  # type: ignore[no-untyped-def]
    # French query term matches the French name; the English term does not (in the fr locale)
    fr = client.get("/api/products?q=Aurora", headers={"Accept-Language": "fr"}).json()
    assert {p["slug"] for p in fr["data"]} == {"aurora"}
