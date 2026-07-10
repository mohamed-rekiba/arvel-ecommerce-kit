"""K3 primary acceptance gate: the routing-groups refactor of ``routes/api.py`` must produce a
byte-identical resolved route table to the flat version it replaced. ``tests/fixtures/
route_table_golden.json`` was captured from the pre-refactor route list (see K3 architecture doc);
this test rebuilds the same canonical tuple from the live app and asserts set-equality. Any
prefix/name miscompose, dropped ``.status(200)``, or doubled ``security`` scheme fails it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_GOLDEN = Path(__file__).parent / "fixtures" / "route_table_golden.json"


def _route_table() -> list[dict[str, Any]]:
    from bootstrap.app import create_app

    app = create_app()
    app.as_asgi()  # runs bootstrap_app: loads routes/api.py onto the router singleton
    router = app.make("router")

    table = [
        {
            "methods": sorted(route.methods),
            "path": route.path,
            "name": route.name,
            # order preserved: DR-0052 group composition is order-sensitive (a route can carry
            # ["bearer","oidc"]), so sorting would discard information a regression could hide in.
            "middleware": [mw.__qualname__ for mw in route.middlewares],
            "security": list(route.security),
            "status_code": route.status_code,
            "group": route.group,
            "domain": route.domain,
        }
        for route in router.routes()
    ]
    table.sort(key=lambda r: (r["path"], r["name"] or "", tuple(r["methods"])))
    return table


def _as_set(table: list[dict[str, Any]]) -> set[tuple[Any, ...]]:
    return {
        (
            tuple(r["methods"]),
            r["path"],
            r["name"],
            tuple(r["middleware"]),
            tuple(r["security"]),
            r["status_code"],
            r["group"],
            r["domain"],
        )
        for r in table
    }


def test_route_table_is_set_equal_to_the_pre_refactor_golden() -> None:
    golden = json.loads(_GOLDEN.read_text())
    live = _route_table()

    golden_set = _as_set(golden)
    live_set = _as_set(live)

    # length check first: set-equality alone would pass vacuously if a route were registered
    # twice with an identical canonical tuple (the duplicate collapses in the set).
    assert len(live) == len(golden), (
        f"route count changed: {len(golden)} -> {len(live)}"
    )

    missing = golden_set - live_set  # routes the refactor dropped or changed
    added = live_set - golden_set  # routes the refactor introduced or changed
    assert not missing and not added, (
        f"route table drifted — missing={missing} added={added}"
    )
