"""S15 — the coupon last-use race on real Postgres: two checkouts race for a code with ONE
remaining use; the row lock serializes redemption so exactly one order gets the discount and the
loser fails with the exhausted-code 422 (fully rolled back — no order, stock untouched)."""

from __future__ import annotations

import asyncio
import threading

import pytest

from tests.checkout_helpers import checkout_body
from tests.integration.test_queue_rail import _seed_shop

pytestmark = pytest.mark.integration


def test_two_checkouts_race_for_the_last_use(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_shop(postgres_url))

    async def _seed_coupon() -> None:
        import sqlalchemy as sa
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(postgres_url)
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO coupons (code, type, value, min_subtotal_cents, usage_limit, "
                    "per_customer_limit, uses, active, created_at, updated_at) "
                    "VALUES ('LAST1', 'percent', 10, 0, 1, NULL, 0, TRUE, now(), now())"
                )
            )
        await engine.dispose()

    asyncio.run(_seed_coupon())
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from litestar.testing import TestClient

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as client:
        # two separate GUEST carts, both with the coupon applied
        tokens: list[str] = []
        for _ in range(2):
            cart_token = client.post(
                "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}
            ).json()["cart_token"]
            applied = client.post(
                "/api/cart/coupon",
                json={"code": "LAST1"},
                headers={"X-Cart-Token": cart_token},
            )
            assert applied.status_code == 200
            tokens.append(cart_token)

        results: list[int] = []

        def _checkout(cart_token: str, email: str) -> None:
            results.append(
                client.post(
                    "/api/checkout",
                    json=checkout_body(email=email),
                    headers={"X-Cart-Token": cart_token},
                ).status_code
            )

        threads = [
            threading.Thread(target=_checkout, args=(tokens[0], "a@example.com")),
            threading.Thread(target=_checkout, args=(tokens[1], "b@example.com")),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # exactly one winner; the loser saw the exhausted-code 422
        assert sorted(results) == [201, 422]
