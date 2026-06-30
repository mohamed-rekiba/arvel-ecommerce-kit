"""Debounced catalog-visibility refresh — a publish change flags the views dirty (observer →
mark_dirty); the scheduled refresh_if_dirty coalesces a burst into one refresh and clears the flag.
On sqlite the refresh is a no-op (the framework degraded the MVs to live views); the flag logic is
what we assert here. (CONCURRENTLY + the observer are verified on live Postgres.)"""

from __future__ import annotations

from pathlib import Path

import pytest

from arvel.cache import CacheManager
from arvel.database import ConnectionResolver
from arvel.kernel import Application, set_application


@pytest.fixture
def app(tmp_path: Path):  # type: ignore[no-untyped-def]
    application = Application()
    application.instance("cache", CacheManager(application).create_array_driver())
    application.instance(
        "db", ConnectionResolver({"default": {"url": f"sqlite+aiosqlite:///{tmp_path / 'v.sqlite'}"}})
    )
    set_application(application)
    yield application
    set_application(None)


async def test_refresh_if_dirty_is_debounced(app) -> None:  # type: ignore[no-untyped-def]
    from app.services.catalog_visibility_service import CatalogVisibilityService as V

    assert await V.refresh_if_dirty() is False  # nothing changed → no refresh
    await V.mark_dirty()
    await V.mark_dirty()  # a burst coalesces to one dirty flag
    assert await V.refresh_if_dirty() is True  # dirty → refresh (no-op on sqlite) + clear
    assert await V.refresh_if_dirty() is False  # flag cleared → no repeat refresh
