"""S8 — the guest→user cart merge on real PG + Valkey: merged quantities (stock-capped), the
retired guest cart, and the CACHED subtotal invalidated for both carts on merge."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from tests.integration.test_queue_rail import _seed_shop

pytestmark = pytest.mark.integration


def test_merge_on_pg_invalidates_cached_totals(
    postgres_url: str, valkey_url: str, kit_app: Any
) -> None:
    asyncio.run(_seed_shop(postgres_url))
    env = dict(DATABASE_URL=postgres_url, CACHE_STORE="redis", CACHE_URL=valkey_url)
    with kit_app(**env) as client:
        # the user's cart holds 1×TEE-S — and its total is CACHED in Valkey by the read
        auth = {
            "Authorization": f"Bearer {client.post('/api/login', json={'email': 'cara@example.com', 'password': 'secret-cara'}).json()['token']}"
        }
        client.post(
            "/api/cart/items",
            json={"product_variant_id": 1, "quantity": 1},
            headers=auth,
        )
        assert client.get("/api/cart", headers=auth).json()["total_cents"] == 2000

        # a guest cart holds 2 more of the same variant
        guest_token = client.post(
            "/api/cart/items", json={"product_variant_id": 1, "quantity": 2}
        ).json()["cart_token"]

        # sign in with the guest token → merge; the CACHED user total must be invalidated,
        # not served stale from Valkey
        merged = {
            "Authorization": f"Bearer {client.post('/api/login', json={'email': 'cara@example.com', 'password': 'secret-cara'}, headers={'X-Cart-Token': guest_token}).json()['token']}"
        }
        cart = client.get("/api/cart", headers=merged).json()
        assert cart["items"][0]["quantity"] == 3
        assert cart["total_cents"] == 6000  # a stale cached 2000 would fail here

        # the guest cart is gone
        assert (
            client.get("/api/cart", headers={"X-Cart-Token": guest_token}).json()[
                "items"
            ]
            == []
        )
