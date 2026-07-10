"""K12 — `settings_service.all_settings()`'s stale-while-revalidate swap
(`Cache.remember` → `Cache.flexible`) on the real cache backend + real Postgres.

Timing is driven by an injectable ``clock`` (a mutable ``t = [0.0]``) plus
``Cache.wait_for_pending_revalidations()`` — no real sleeps. The single-flight assertion needs the
real NX-backed ``add`` (the array driver can mask a dedupe bug), so this runs on testcontainers
Valkey; the background refresh's DB read needs a real Postgres to prove it actually reaches the
database outside request scope, not just "doesn't error"."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from arvel import Cache
from arvel.database import ConnectionResolver, Migrator, discover_migrations
from arvel.kernel import set_application
from arvel.kernel.bootstrap import bootstrap_app

from app.models.setting import Setting
from app.services import settings_service
from app.services.settings_service import _CACHE_KEY

pytestmark = pytest.mark.integration


async def _boot_app(
    postgres_url: str, valkey_url: str, monkeypatch: pytest.MonkeyPatch
) -> Any:
    """Migrate a clean schema (the PG container is session-scoped; each test starts clean) and
    boot the kit the way a real server process does, wired to real Postgres + real Valkey."""
    db = ConnectionResolver({"default": {"url": postgres_url}})
    migrator = Migrator(db)
    await migrator.drop_all()
    await migrator.run(discover_migrations(["database/migrations"]))
    await db.dispose()

    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("CACHE_STORE", "redis")
    monkeypatch.setenv("CACHE_URL", valkey_url)
    from bootstrap.app import create_app

    app = create_app()
    bootstrap_app(app)
    await app.boot()
    return app


async def test_stale_served_single_flight_and_background_refresh_reaches_the_db(
    postgres_url: str, valkey_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _boot_app(postgres_url, valkey_url, monkeypatch)
    try:
        await Cache.flush()  # the Valkey container is session-scoped — start clean
        count = {"n": 0}
        # the real backend is fast enough that an ungated background refresh can finish (and
        # overwrite the entry) before every one of the N concurrent readers has even done its own
        # `get` — a real race, not a framework bug (see impl notes). Gate the *revalidation* call
        # (the 2nd+ loader invocation) so it can't touch the DB until all N reads are in, making
        # the single-flight proof deterministic without masking anything real: single-flight is
        # about the loader running once, not about winning a race against real network latency.
        release = asyncio.Event()

        async def loader() -> dict[str, str]:
            count["n"] += 1
            if count["n"] > 1:
                await release.wait()
            rows = await Setting.all()
            return {r.key: r.value for r in rows}

        await Setting.create(key="store.email", value="v1@example.com")
        t = [0.0]

        primed = await Cache.flexible(
            _CACHE_KEY, (300, 600), loader, clock=lambda: t[0]
        )
        assert primed["store.email"] == "v1@example.com"
        assert count["n"] == 1  # cold miss -> one inline load

        # past `fresh`; change the underlying row so a refresh that truly reaches the DB is
        # observable on the next hit (not just "no exception")
        t[0] = 301.0
        await Setting.where("key", "store.email").update({"value": "v2@example.com"})

        results = await asyncio.gather(
            *[
                Cache.flexible(_CACHE_KEY, (300, 600), loader, clock=lambda: t[0])
                for _ in range(8)
            ]
        )
        assert all(
            r["store.email"] == "v1@example.com" for r in results
        )  # all served stale
        assert count["n"] == 2  # single-flight: exactly one background refresh, not 8

        release.set()  # let the gated revalidation reach the DB
        await Cache.wait_for_pending_revalidations()

        refreshed = await Cache.flexible(
            _CACHE_KEY, (300, 600), loader, clock=lambda: t[0]
        )
        assert (
            refreshed["store.email"] == "v2@example.com"
        )  # refresh actually reached the DB
        assert count["n"] == 2  # this hit landed on the now-fresh entry, no extra load
    finally:
        set_application(None)


async def test_cold_miss_computes_inline(
    postgres_url: str, valkey_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _boot_app(postgres_url, valkey_url, monkeypatch)
    try:
        await Cache.flush()
        assert await settings_service.all_settings() == settings_service.DEFAULTS
    finally:
        set_application(None)


async def test_refresh_failure_serves_stale_and_does_not_clobber(
    postgres_url: str, valkey_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _boot_app(postgres_url, valkey_url, monkeypatch)
    try:
        await Cache.flush()
        t = [0.0]

        async def ok_loader() -> dict[str, str]:
            return {"store.email": "v1@example.com"}

        async def failing_loader() -> dict[str, str]:
            raise RuntimeError("boom")

        primed = await Cache.flexible(
            _CACHE_KEY, (300, 600), ok_loader, clock=lambda: t[0]
        )
        assert primed["store.email"] == "v1@example.com"

        t[0] = 301.0
        stale_hit = await Cache.flexible(
            _CACHE_KEY, (300, 600), failing_loader, clock=lambda: t[0]
        )
        assert (
            stale_hit["store.email"] == "v1@example.com"
        )  # no exception reached the caller

        await (
            Cache.wait_for_pending_revalidations()
        )  # background failure: logged, not raised

        still_stale = await Cache.flexible(
            _CACHE_KEY, (300, 600), ok_loader, clock=lambda: t[0]
        )
        assert (
            still_stale["store.email"] == "v1@example.com"
        )  # failed refresh didn't overwrite
    finally:
        set_application(None)
