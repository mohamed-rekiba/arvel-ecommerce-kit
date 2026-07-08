"""Cursor (keyset) product feed on real Postgres — walks GET /api/products/feed via next_cursor and
proves the drift-free property (a product published mid-scroll never makes a page repeat or skip).
Postgres serves storefront retrievability from the ``retrievable_products`` materialized view, so the
seed and the mid-scroll insert both REFRESH it — the deployment reality sqlite unit tests can't show.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant

pytestmark = pytest.mark.integration

_MODELS = (Category, Product, ProductVariant)


async def _refresh(url: str) -> None:
    """Refresh the retrievability matviews so freshly-seeded/inserted rows become visible."""
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(sa.text("REFRESH MATERIALIZED VIEW retrievable_products"))
        await conn.execute(sa.text("REFRESH MATERIALIZED VIEW retrievable_categories"))
    await engine.dispose()


async def _make_product(cat_id: int, slug: str, price_cents: int) -> None:
    p = await Product.create(
        category_id=cat_id,
        translations={"en": {"name": slug, "description": "feed item"}},
        slug=slug,
        price_cents=price_cents,
        currency="USD",
        status=ProductStatus.ACTIVE,
        published=True,
    )
    await ProductVariant.create(product_id=p.id, sku=f"{slug}-S", name="S", stock=5)


async def _seed_catalog(url: str, count: int) -> None:
    db = ConnectionResolver({"default": {"url": url}})
    migrator = Migrator(db)
    await migrator.drop_all()  # session-scoped PG container — start clean
    await migrator.run(discover_migrations(["database/migrations"]))
    for model in _MODELS:
        model.set_connection(db)
    try:
        cat = await Category.create(
            translations={"en": {"name": "Feed"}}, slug="feed", published=True
        )
        for i in range(count):
            await _make_product(cat.id, f"feed-prod-{i:02d}", 1000 + i)
    finally:
        for model in _MODELS:
            model.set_connection(None)
        await db.dispose()
    await _refresh(url)


async def _insert_one(url: str, slug: str) -> None:
    """Insert one retrievable product mid-scroll (and refresh the matview so it is truly visible)."""
    db = ConnectionResolver({"default": {"url": url}})
    for model in _MODELS:
        model.set_connection(db)
    try:
        cat = await Category.where("slug", "feed").first_or_fail()
        await _make_product(cat.id, slug, 1005)
    finally:
        for model in _MODELS:
            model.set_connection(None)
        await db.dispose()
    await _refresh(url)


def test_cursor_feed_walks_and_is_drift_free_on_pg(postgres_url: str, kit_app: Any) -> None:
    asyncio.run(_seed_catalog(postgres_url, 12))
    with kit_app(DATABASE_URL=postgres_url) as client:
        # 1) walk the whole feed via next_cursor: every row once, slug-ordered, null-terminated
        seen: list[str] = []
        cursor: str | None = None
        pages = 0
        while True:
            params: dict[str, object] = {"per_page": 5}
            if cursor:
                params["cursor"] = cursor
            body = client.get("/api/products/feed", params=params).json()
            pages += 1
            seen.extend(p["slug"] for p in body["data"])
            cursor = body.get("next_cursor")
            if not cursor:
                break
            assert pages < 10, "cursor never terminated"
        assert pages == 3  # 5 + 5 + 2
        assert seen == [f"feed-prod-{i:02d}" for i in range(12)]

        # 2) drift-free: publish a product that sorts *before* the cursor between page loads; keyset
        # seeks past the last-seen slug, so page 2 neither repeats nor skips (offset would duplicate).
        page1 = client.get("/api/products/feed", params={"per_page": 5}).json()
        assert [p["slug"] for p in page1["data"]] == [
            f"feed-prod-{i:02d}" for i in range(5)
        ]
        boundary_cursor = page1["next_cursor"]
        asyncio.run(_insert_one(postgres_url, "feed-prod-02a"))  # sorts between 02 and 03
        page2 = client.get(
            "/api/products/feed", params={"per_page": 5, "cursor": boundary_cursor}
        ).json()
        page2_slugs = [p["slug"] for p in page2["data"]]
        assert page2_slugs == [f"feed-prod-{i:02d}" for i in range(5, 10)]
        # the new row is retrievable now, but behind the cursor → keyset correctly excludes it
        assert "feed-prod-02a" not in page2_slugs
