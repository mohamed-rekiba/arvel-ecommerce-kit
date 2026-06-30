"""Marks the catalog-visibility views dirty when a product / category / vendor changes, so the
debounced refresh (scheduled `refresh_if_dirty`) recomputes which rows are retrievable.

Marking is cheap (a cache flag) and coalesced downstream, so flagging on every save is fine — the
refresh is bounded by the schedule interval regardless. (Optimization later: only flag when a
visibility-affecting field — published / vendor_id / category_id / parent_id — actually changed.)
"""

from typing import Any

from app.services.catalog_visibility_service import CatalogVisibilityService


class PublishObserver:
    async def saved(self, model: Any) -> None:
        await CatalogVisibilityService.mark_dirty()

    async def deleted(self, model: Any) -> None:
        await CatalogVisibilityService.mark_dirty()
