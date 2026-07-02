"""S11 — vendor publish gating on real Postgres: unpublishing a vendor flags the MATERIALIZED
retrievable views dirty; the debounced refresh (the scheduled tick's exact code path) recomputes
them and the storefront drops the vendor's products. Republish restores them."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from tests.integration.test_queue_rail import _seed_shop

pytestmark = pytest.mark.integration


def test_vendor_unpublish_flows_through_the_debounced_refresh(
    postgres_url: str, valkey_url: str, kit_app: Any
) -> None:
    asyncio.run(_seed_shop(postgres_url))

    async def _attach_vendor() -> None:
        # the shared seed's tee is first-party; hand it to a published vendor for this test
        import sqlalchemy as sa
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(postgres_url)
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO vendors (name, slug, published, created_at, updated_at) "
                    "VALUES ('Nordic Audio', 'nordic-audio', TRUE, now(), now())"
                )
            )
            await conn.execute(
                sa.text(
                    "UPDATE products SET vendor_id = (SELECT id FROM vendors LIMIT 1)"
                )
            )
            await conn.execute(
                sa.text("REFRESH MATERIALIZED VIEW retrievable_products")
            )
            await conn.execute(
                sa.text("REFRESH MATERIALIZED VIEW retrievable_categories")
            )
        await engine.dispose()

    asyncio.run(_attach_vendor())
    env = dict(DATABASE_URL=postgres_url, CACHE_STORE="redis", CACHE_URL=valkey_url)
    with kit_app(**env) as client:
        admin = {
            "Authorization": f"Bearer {client.post('/api/login', json={'email': 'admin@example.com', 'password': 'secret-admin'}).json()['token']}"
        }
        vendors = client.get("/api/admin/vendors", headers=admin).json()
        assert len(vendors) == 1
        assert client.get("/api/products/tee").status_code == 200

        # unpublish → the MVs are stale until the debounced refresh runs (that's the design)
        client.put(
            f"/api/admin/vendors/{vendors[0]['id']}",
            json={"published": False},
            headers=admin,
        )

        # run the EXACT scheduled tick (Schedule.call(refresh_if_dirty)) — dirty → one refresh
        async def _tick() -> bool:
            from app.services.catalog_visibility_service import CatalogVisibilityService

            return await CatalogVisibilityService.refresh_if_dirty()

        with client.portal() as portal:
            assert (
                portal.call(_tick) is True
            )  # dirty → exactly one CONCURRENTLY refresh

            assert (
                client.get("/api/products/tee").status_code == 404
            )  # gone from the storefront

            # a clean tick no-ops (debounce)
            assert portal.call(_tick) is False

            # republish + refresh → back
            client.put(
                f"/api/admin/vendors/{vendors[0]['id']}",
                json={"published": True},
                headers=admin,
            )
            assert portal.call(_tick) is True
            assert client.get("/api/products/tee").status_code == 200
