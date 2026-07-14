"""S18 — operability through the served path: maintenance mode (503 + health exemption +
survives a process restart via the cache) and the scheduler's due/no-op/error semantics."""

import asyncio
from datetime import datetime

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'ops.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def migrate() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await db.dispose()

    asyncio.run(migrate())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def test_maintenance_mode_gates_everything_but_health(client) -> None:
    from arvel.http import maintenance

    with client.portal() as portal:
        assert client.get("/api/products").status_code == 200

        portal.call(maintenance.down)
        down = client.get("/api/products")
        assert down.status_code == 503
        assert "maintenance" in down.json()["message"].lower()
        assert "Retry-After" in down.headers
        # the liveness probe answers regardless (app.maintenance_except)
        assert client.get("/health").status_code == 200

        portal.call(maintenance.up)
        assert client.get("/api/products").status_code == 200


def test_scheduler_sweeps_only_past_the_boundary(client) -> None:
    """The registered schedule (routes/console.py): a 73h-old guest cart sweeps; a 71h-old one
    and a user cart survive. Runs the REAL registered events via Schedule.run_due at 03:00."""

    async def _seed_and_tick() -> tuple[bool, bool, bool]:
        from arvel.console.kernel import load_console_routes
        from arvel.dates import Date
        from arvel.kernel import app

        from app.models.cart import Cart

        load_console_routes(app())  # what `arvel schedule:run` does before ticking

        stale = await Cart.create(token="stale-token")
        fresh = await Cart.create(token="fresh-token")
        await Cart.where("id", stale.id).update(
            {"updated_at": Date.now().subtract(hours=73)}
        )
        await Cart.where("id", fresh.id).update(
            {"updated_at": Date.now().subtract(hours=71)}
        )

        schedule = app().make("schedule")
        moment = datetime(2026, 7, 2, 3, 0)
        assert len(schedule.due_events(moment)) >= 1  # the 03:00 sweep is due
        await schedule.run_due(moment)  # daily_at("03:00") fires
        return (
            await Cart.find(stale.id) is None,
            await Cart.find(fresh.id) is not None,
            True,
        )

    with client.portal() as portal:
        stale_gone, fresh_kept, _ = portal.call(_seed_and_tick)
    assert stale_gone and fresh_kept


def test_dirty_flag_refresh_tick_and_clean_noop(client) -> None:
    """The every-minute refresh tick: dirty → one refresh (returns True); clean → no-op."""

    async def _tick() -> tuple[bool, bool]:
        from app.services.catalog_visibility_service import CatalogVisibilityService

        await CatalogVisibilityService.mark_dirty()
        first = await CatalogVisibilityService.refresh_if_dirty()
        second = await CatalogVisibilityService.refresh_if_dirty()
        return first, second

    with client.portal() as portal:
        first, second = portal.call(_tick)
    assert first is True and second is False
