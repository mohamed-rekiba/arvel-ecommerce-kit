"""K6 — the abandoned-cart sweep's REAL firing path, and the `search:reindex` output handle, both
driven through the served console dispatch (not a direct function call), on real PostgreSQL.

`tests/test_background.py::test_abandoned_cart_sweep_deletes_stale_guest_carts` already proves
`sweep_abandoned_carts()`'s SQL is correct — it calls the task directly. That tells us nothing
about whether the task is actually WIRED to fire at 03:00: cadence match -> `due_events` selection
-> `Schedule.run_due(moment)` running the callback inline. This drives that real seam instead.
"""

from __future__ import annotations

import contextlib
import io
from datetime import datetime
from typing import Any

import pytest

from arvel.console.kernel import Cli, load_console_routes
from arvel.database import ConnectionResolver
from arvel.kernel import set_application
from arvel.kernel.bootstrap import bootstrap_app

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.user import User
from tests.integration.test_queue_rail import _seed_shop

pytestmark = pytest.mark.integration

# Far enough in the past to clear the 72h sweep threshold no matter when the suite actually runs —
# the *moment* being simulated is 2026-01-01 03:00, but `sweep_abandoned_carts` itself compares
# against real wall-clock now (`Date.now()`), not the simulated moment.
_STALE = datetime(2020, 1, 1)


async def _boot_console_app(url: str) -> Any:
    """Boot a kit application the way a real `arvel <command>` process does: sync bootstrap (which
    registers `search:reindex` — a provider `commands()` class, not a closure), async provider
    boot, then load `routes/console.py` — the step that registers the nightly sweep onto the bound
    `schedule`."""
    from bootstrap.app import create_app

    app = create_app()
    bootstrap_app(app)
    await app.boot()
    load_console_routes(app)
    return app


async def _seed_carts(url: str) -> dict[str, int]:
    """`_seed_shop` gives us a customer (Cara) and one purchasable variant; layer three carts on
    top: a stale guest cart (+ item) that must be swept, and two controls that must survive — a
    stale AUTHENTICATED cart and a fresh guest cart."""
    await _seed_shop(url)
    db = ConnectionResolver({"default": {"url": url}})
    models = (User, Cart, CartItem)
    for model in models:
        model.set_connection(db)
    try:
        cara = await User.where("email", "cara@example.com").first()
        stale_guest = await Cart.create(token="stale-guest")
        await CartItem.create(
            cart_id=stale_guest.id,
            product_variant_id=1,
            quantity=1,
            unit_price_cents=2000,
        )
        stale_user_cart = await Cart.create(user_id=cara.id)
        fresh_guest = await Cart.create(token="fresh-guest")
        await Cart.where("id", stale_guest.id).update({"updated_at": _STALE})
        await Cart.where("id", stale_user_cart.id).update({"updated_at": _STALE})
        return {
            "stale_guest": stale_guest.id,
            "stale_user_cart": stale_user_cart.id,
            "fresh_guest": fresh_guest.id,
        }
    finally:
        for model in models:
            model.set_connection(None)
        await db.dispose()


async def test_scheduler_drain_fires_the_sweep_at_0300_and_skips_at_0301(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = await _seed_carts(postgres_url)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    app = await _boot_console_app(postgres_url)
    try:
        schedule = app.make("schedule")
        # guard against a false negative: if routes/console.py never registered, due_events would
        # be empty here and the deletion assertion below would pass for the wrong reason.
        assert schedule.due_events(datetime(2026, 1, 1, 3, 0))

        await schedule.run_due(
            datetime(2026, 1, 1, 3, 0)
        )  # due (cron "0 3 * * *") — runs inline
        assert await Cart.find(ids["stale_guest"]) is None
        assert await CartItem.where("cart_id", ids["stale_guest"]).count() == 0
        assert (
            await Cart.find(ids["stale_user_cart"]) is not None
        )  # authenticated cart survives
        assert (
            await Cart.find(ids["fresh_guest"]) is not None
        )  # fresh guest cart survives

        # a second stale guest cart, seeded after the 03:00 drain, proves 03:01 is a genuine
        # no-op — not just "nothing left to delete"
        second_stale = await Cart.create(token="stale-guest-2")
        await Cart.where("id", second_stale.id).update({"updated_at": _STALE})

        await schedule.run_due(datetime(2026, 1, 1, 3, 1))  # not due → no-op
        assert await Cart.find(second_stale.id) is not None
    finally:
        set_application(None)


async def test_search_reindex_dispatches_through_the_output_handle(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`search:reindex` runs through the same dispatch a real `arvel search:reindex` process uses
    (`Cli.call`, not a direct function call), with NO sink pre-bound — production never binds one
    either. The "Reindexed N products" line must land on real stdout, exactly like a real process's
    terminal output; this is the path that actually catches a silently-broken output handle (an
    autowired closure param that resolves to a dead sink prints nothing here, and the test fails)."""
    await _seed_shop(postgres_url)
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    await _boot_console_app(
        postgres_url
    )  # sets the active app; Cli.call dispatches against it
    try:
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            exit_code = Cli.call("search:reindex")
        assert exit_code == 0
        assert "Reindexed 1 products into the search engine." in captured.getvalue()
    finally:
        set_application(None)
