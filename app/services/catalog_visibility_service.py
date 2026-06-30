"""Catalog visibility — the bridge between the retrievability materialized views and the storefront.

The storefront only shows *retrievable* products/categories (published, with a published vendor, under
a fully-published category branch, in a non-empty category). That set is precomputed in the
``retrievable_products`` / ``retrievable_categories`` materialized views; this service refreshes them
after a publish change and exposes the id sets the catalog filters by.
"""

from __future__ import annotations

import sqlalchemy as sa

from arvel import DB

_VIEWS = ("retrievable_products", "retrievable_categories")


class CatalogVisibilityService:
    async def refresh(self) -> None:
        """Recompute the views after a publish change. A no-op on sqlite/mysql, where the framework
        degraded the materialized views to live plain views (nothing to refresh)."""
        if DB.engine().dialect.name != "postgresql":
            return
        for view in _VIEWS:
            await DB.execute(sa.text(f"REFRESH MATERIALIZED VIEW {view}"))  # noqa: S608 # nosec B608

    async def retrievable_product_ids(self) -> list[int]:
        rows = await DB.fetch_all(sa.text("SELECT id FROM retrievable_products"))
        return [int(row["id"]) for row in rows]

    async def retrievable_category_ids(self) -> list[int]:
        rows = await DB.fetch_all(sa.text("SELECT id FROM retrievable_categories"))
        return [int(row["id"]) for row in rows]
