"""Catalog visibility — the bridge between the retrievability materialized views and the storefront.

The storefront only shows *retrievable* products/categories (published, with a published vendor, under
a fully-published category branch, in a non-empty category). That set is precomputed in the
``retrievable_products`` / ``retrievable_categories`` materialized views; this service refreshes them
after a publish change and exposes the id sets the catalog filters by.
"""

from __future__ import annotations

import sqlalchemy as sa

from arvel import DB, Cache

_VIEWS = ("retrievable_products", "retrievable_categories")
_DIRTY = "catalog:visibility:dirty"
_LOCK = "catalog:visibility:refresh"


class CatalogVisibilityService:
    @staticmethod
    async def mark_dirty() -> None:
        """Flag the visibility views as stale after a publish change. Cheap — the debounced scheduler
        (or job) coalesces a burst of changes into a single refresh. A no-op outside a booted app (e.g.
        a raw fixture seed that has no cache bound)."""
        from arvel.kernel import has_application

        if not has_application():
            return
        await Cache.put(_DIRTY, value=True, ttl=86400)

    @classmethod
    async def refresh_if_dirty(cls) -> bool:
        """Refresh only if something changed since the last refresh (the debounce tick). Returns whether
        it refreshed. Driven by a scheduled task (every ~30s) and as the reconcile safety net."""
        if not await Cache.get(_DIRTY):
            return False
        await Cache.forget(_DIRTY)  # clear before refreshing → a change mid-refresh re-dirties
        await cls().refresh()
        return True

    async def refresh(self) -> None:
        """Recompute the visibility views. CONCURRENTLY (no read-lock; needs the unique index) on
        Postgres, single-flighted by a cache lock so two refreshes never overlap. A no-op on sqlite,
        where the framework degraded the materialized views to live plain views."""
        if DB.engine().dialect.name != "postgresql":
            return
        async with Cache.lock(_LOCK, ttl=120):
            for view in _VIEWS:
                await DB.execute(sa.text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))  # noqa: S608 # nosec B608
