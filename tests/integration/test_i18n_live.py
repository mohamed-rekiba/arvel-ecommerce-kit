"""S7 — locale projection on real infra: fr content from PG jsonb, COALESCE fallback for a
missing translation, unsupported-locale coercion, and a French search through Meilisearch."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant

pytestmark = pytest.mark.integration

_MODELS = (Category, Product, ProductVariant)


async def _seed_bilingual(url: str) -> None:
    db = ConnectionResolver({"default": {"url": url}})
    migrator = Migrator(db)
    await migrator.drop_all()
    await migrator.run(discover_migrations(["database/migrations"]))
    for model in _MODELS:
        model.set_connection(db)
    try:
        cat = await Category.create(
            translations={"en": {"name": "Lighting"}, "fr": {"name": "Éclairage"}},
            slug="lighting",
            published=True,
        )
        lamp = await Product.create(
            category_id=cat.id,
            translations={
                "en": {"name": "Aurora Lamp", "description": "Warm light."},
                "fr": {"name": "Lampe Aurora", "description": "Lumière chaude."},
            },
            slug="aurora-lamp",
            price_cents=4900,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        # English-only — the fr request must FALL BACK to en, never render blank
        mono = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Plain Sconce", "description": "en only"}},
            slug="plain-sconce",
            price_cents=2900,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        for product in (lamp, mono):
            await ProductVariant.create(
                product_id=product.id,
                sku=f"SKU-{product.id}",
                name="One size",
                price_adjustment_cents=0,
                stock=5,
            )
        import sqlalchemy as sa
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.execute(
                sa.text("REFRESH MATERIALIZED VIEW retrievable_products")
            )
            await conn.execute(
                sa.text("REFRESH MATERIALIZED VIEW retrievable_categories")
            )
        await engine.dispose()
    finally:
        for model in _MODELS:
            model.set_connection(None)
        await db.dispose()


def test_locale_projection_fallback_and_french_search(
    postgres_url: str,
    meilisearch: dict[str, str],
    kit_app: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asyncio.run(_seed_bilingual(postgres_url))
    env = dict(
        DATABASE_URL=postgres_url,
        SEARCH_DRIVER="meilisearch",
        MEILISEARCH_URL=meilisearch["url"],
        MEILISEARCH_KEY=meilisearch["key"],
    )
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    async def _index() -> None:
        # index through the same surface search:reindex uses — its own boot + loop, torn down
        # before the served client starts (a shared loop-bound pool would cross event loops)
        from arvel.kernel import set_application
        from arvel.kernel.bootstrap import bootstrap_app

        from bootstrap.app import create_app

        app = create_app()
        bootstrap_app(app)
        await app.boot()
        try:
            await Product.make_all_searchable()
        finally:
            set_application(None)

    asyncio.run(_index())

    with kit_app(**env) as client:
        fr = {"Accept-Language": "fr"}
        products = client.get("/api/products", headers=fr).json()["data"]
        by_slug = {p["slug"]: p["translation"] for p in products}
        assert by_slug["aurora-lamp"]["name"] == "Lampe Aurora"
        # fallback: the en content serves where fr is missing — never a blank
        assert by_slug["plain-sconce"]["name"] == "Plain Sconce"

        categories = client.get("/api/categories", headers=fr).json()
        assert categories[0]["translation"]["name"] == "Éclairage"

        # an unsupported locale is coerced to the default, not interpolated into SQL
        weird = client.get("/api/products", headers={"Accept-Language": "xx-e'vil"})
        assert weird.status_code == 200
        assert weird.json()["data"][0]["translation"]["name"] in (
            "Aurora Lamp",
            "Plain Sconce",
        )

        # French search through Meilisearch (driver-aware q=)
        deadline = time.time() + 30
        hits: list[str] = []
        while time.time() < deadline:
            hits = [
                p["slug"]
                for p in client.get("/api/products?q=Lampe", headers=fr).json()["data"]
            ]
            if hits:
                break
            time.sleep(0.5)
        assert hits == ["aurora-lamp"]
