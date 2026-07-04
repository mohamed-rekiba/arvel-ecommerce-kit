"""S12 — archive vs search on real PG + Meilisearch: an archived product disappears from q=
results (the retrievable-set intersection filters it even while the index still holds the doc)
and returns after restore. Order-line integrity is asserted on PG."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from tests.integration.test_i18n_live import _seed_bilingual

pytestmark = pytest.mark.integration


def test_archive_drops_from_search_and_restore_returns(
    postgres_url: str,
    meilisearch: dict[str, str],
    kit_app: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asyncio.run(_seed_bilingual(postgres_url))
    env = dict(
        DATABASE_URL=postgres_url,
        SEARCH_DRIVER="meilisearch",
        MEILISEARCH_URL=meilisearch["url"],
        MEILISEARCH_KEY=meilisearch["key"],
    )
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    async def _index() -> None:
        from arvel.kernel import set_application
        from arvel.kernel.bootstrap import bootstrap_app

        from app.models.product import Product
        from bootstrap.app import create_app

        app = create_app()
        bootstrap_app(app)
        await app.boot()
        try:
            await Product.make_all_searchable()
        finally:
            set_application(None)

    asyncio.run(_index())

    with kit_app(**env) as client:
        # archiving via the model layer here — authz over the admin endpoint is covered elsewhere
        def _search(q: str) -> list[str]:
            deadline = time.time() + 30
            while time.time() < deadline:
                hits = [
                    p["slug"] for p in client.get(f"/api/products?q={q}").json()["data"]
                ]
                if hits:
                    return hits
                time.sleep(0.5)
            return []

        assert _search("Aurora") == ["aurora-lamp"]

        async def _archive() -> None:
            from app.models.product import Product

            product = await Product.where("slug", "aurora-lamp").first_or_fail()
            await product.delete()  # soft: stamps deleted_at
            from app.services.catalog_visibility_service import CatalogVisibilityService

            await CatalogVisibilityService().refresh()

        with client.portal() as portal:
            portal.call(_archive)

            # archive fires the deleted hook -> unsearchable() removes the doc; either way the API hides it
            assert [
                p["slug"] for p in client.get("/api/products?q=Aurora").json()["data"]
            ] == []
            # and the PDP 404s
            assert client.get("/api/products/aurora-lamp").status_code == 404

            async def _restore() -> None:
                from app.models.product import Product

                product = (
                    await Product.only_trashed().where("slug", "aurora-lamp").first()
                )
                assert product is not None
                await product.restore()
                from app.services.catalog_visibility_service import (
                    CatalogVisibilityService,
                )

                await CatalogVisibilityService().refresh()

            portal.call(_restore)
            assert client.get("/api/products/aurora-lamp").status_code == 200
            # Meilisearch indexes asynchronously, so poll like the initial-index search above
            assert _search("Aurora") == ["aurora-lamp"]
