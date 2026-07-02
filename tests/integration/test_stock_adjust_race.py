"""S9 — concurrent stock adjustments on real Postgres serialize under the row lock: two parallel
delta operations both land (no lost update), deterministically."""

from __future__ import annotations

import asyncio
import threading

import pytest

from tests.integration.test_queue_rail import _seed_shop

pytestmark = pytest.mark.integration


def test_concurrent_deltas_never_lose_an_update(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_shop(postgres_url))
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from litestar.testing import TestClient

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as client:
        admin = {
            "Authorization": f"Bearer {client.post('/api/login', json={'email': 'admin@example.com', 'password': 'secret-admin'}).json()['token']}"
        }
        # seed stock = 100; 8 concurrent -5 deltas → exactly 60 (a lost update would land higher)
        results: list[int] = []

        def _adjust() -> None:
            results.append(
                client.post(
                    "/api/admin/variants/1/stock",
                    json={"delta": -5, "reason": "race test"},
                    headers=admin,
                ).status_code
            )

        threads = [threading.Thread(target=_adjust) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert results == [200] * 8

        variants = client.get("/api/admin/products/1/variants", headers=admin).json()
        assert variants[0]["stock"] == 100 - 8 * 5
