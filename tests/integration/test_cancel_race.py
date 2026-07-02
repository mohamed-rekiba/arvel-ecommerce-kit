"""S5 — concurrent cancellation on real Postgres: two simultaneous cancels of the same order
produce exactly ONE transition and exactly ONE stock restoration (the order row is re-read under
SELECT ... FOR UPDATE inside the transaction, so the loser sees CANCELLED and 422s)."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import pytest
from litestar.testing import TestClient

from tests.checkout_helpers import checkout_body
from tests.integration.test_queue_rail import _seed_shop

pytestmark = pytest.mark.integration


def test_concurrent_cancels_restock_exactly_once(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_shop(postgres_url))
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as client:
        cart_token = client.post(
            "/api/cart/items", json={"product_variant_id": 1, "quantity": 5}
        ).json()["cart_token"]
        order = client.post(
            "/api/checkout",
            json=checkout_body(email="guest@example.com"),
            headers={"X-Cart-Token": cart_token},
        ).json()
        order_id, token = order["id"], order["token"]
        headers = {"X-Order-Token": token}

        # stock went 100 → 95 at checkout
        results: list[int] = []

        def _cancel() -> None:
            results.append(
                client.post(
                    f"/api/orders/{order_id}/cancel", headers=headers
                ).status_code
            )

        threads = [threading.Thread(target=_cancel) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # exactly one winner; the loser hit the state machine
        assert sorted(results) == [200, 422]

        shown = client.get(f"/api/orders/{order_id}", headers=headers).json()
        assert shown["status"] == "cancelled"

        # exactly one restock: 95 + 5 = 100, not 105
        product: dict[str, Any] = client.get("/api/products/tee").json()
        assert product["variants"][0]["stock"] == 100
