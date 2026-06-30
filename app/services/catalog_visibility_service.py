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

    @staticmethod
    def retrievable_product_ids_subquery() -> sa.Select[tuple[int]]:
        """A subquery of retrievable product ids — pass to where_in so the storefront filters DB-side
        (WHERE id IN (SELECT id FROM retrievable_products)) in one query, no app-side id list."""
        view = sa.table("retrievable_products", sa.column("id"))
        return sa.select(view.c.id)

    @staticmethod
    def retrievable_category_ids_subquery() -> sa.Select[tuple[int]]:
        view = sa.table("retrievable_categories", sa.column("id"))
        return sa.select(view.c.id)

    @staticmethod
    async def visible_product_ids_among(ids: list[int]) -> set[int]:
        """Which of ``ids`` are retrievable — for annotating an admin page with is_visible (one query
        bounded by the page size, not the whole catalog)."""
        if not ids:
            return set()
        view = sa.table("retrievable_products", sa.column("id"))
        rows = await DB.fetch_all(sa.select(view.c.id).where(view.c.id.in_(ids)))
        return {int(row["id"]) for row in rows}

    @staticmethod
    async def visible_category_ids_among(ids: list[int]) -> set[int]:
        if not ids:
            return set()
        view = sa.table("retrievable_categories", sa.column("id"))
        rows = await DB.fetch_all(sa.select(view.c.id).where(view.c.id.in_(ids)))
        return {int(row["id"]) for row in rows}
