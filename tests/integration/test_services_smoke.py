"""S1 — one real-service smoke test per infra service, each driving the arvel module for that
service **through the kit's production boot** (`create_app`), not a bespoke harness.

These are the tier's reference tests: later stories add feature-level integration tests beside
them. A closing test proves the tier fails loudly when a service is dead (no silent fallback).
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

import pytest

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant

pytestmark = pytest.mark.integration

_SEED_MODELS = (Category, Product, ProductVariant)


async def _seed_catalog(url: str) -> None:
    """Migrate + seed one retrievable product ("Aurora Lamp") on the given database."""
    db = ConnectionResolver({"default": {"url": url}})
    await Migrator(db).run(discover_migrations(["database/migrations"]))
    for model in _SEED_MODELS:
        model.set_connection(db)
    try:
        cat = await Category.create(
            translations={"en": {"name": "Lighting"}}, slug="lighting", published=True
        )
        product = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Aurora Lamp", "description": "Warm light."}},
            slug="aurora-lamp",
            price_cents=4900,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        await ProductVariant.create(
            product_id=product.id,
            sku="AURORA-1",
            name="One size",
            price_adjustment_cents=0,
            stock=5,
        )
        if url.startswith("postgresql"):
            # on PG the retrievable_* views are MATERIALIZED — recompute after seeding (the same
            # refresh db:seed / the debounced scheduler perform; sqlite degrades to live views)
            import sqlalchemy as sa
            from sqlalchemy.ext.asyncio import create_async_engine

            engine = create_async_engine(url)
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text("REFRESH MATERIALIZED VIEW retrievable_products")
                )
                await conn.execute(
                    sa.text("REFRESH MATERIALIZED VIEW retrievable_categories")
                )
            await engine.dispose()
    finally:
        for model in _SEED_MODELS:
            model.set_connection(None)
        await db.dispose()


def test_postgres_serves_catalog(postgres_url: str, kit_app: Any) -> None:
    """arvel.database on real Postgres: migrate, seed, and read through the served catalog API."""
    asyncio.run(_seed_catalog(postgres_url))
    with kit_app(DATABASE_URL=postgres_url) as client:
        resp = client.get("/api/products")
        assert resp.status_code == 200
        names = [p["translation"]["name"] for p in resp.json()["data"]]
        assert "Aurora Lamp" in names


def test_valkey_backs_cart_cache(valkey_url: str, kit_app: Any, tmp_path: Any) -> None:
    """arvel.cache on real Valkey: the served cart flow writes its cached subtotal to Valkey."""
    import redis

    db_url = f"sqlite+aiosqlite:///{tmp_path / 'valkey.sqlite'}"
    asyncio.run(_seed_catalog(db_url))
    with kit_app(
        DATABASE_URL=db_url, CACHE_STORE="redis", CACHE_URL=valkey_url
    ) as client:
        added = client.post(
            "/api/cart/items", json={"product_variant_id": 1, "quantity": 2}
        )
        assert added.status_code == 201
        token = added.json()["cart_token"]
        shown = client.get("/api/cart", headers={"X-Cart-Token": token})
        assert shown.status_code == 200
        assert shown.json()["total_cents"] == 2 * 4900
    # the subtotal was cached in Valkey by the served path — visible as a real key on the wire
    r = redis.Redis.from_url(valkey_url)
    assert any(b"cart" in key for key in r.keys("*"))


async def test_rabbitmq_worker_consumes_kit_job(
    rabbitmq_url: str, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """arvel.queue on real RabbitMQ: a kit job dispatched through the kit boot round-trips the
    broker and its side effect (the fulfilment metric) lands — dispatch, consume, execute."""
    import contextlib

    from arvel import Cache
    from arvel.kernel import set_application

    from app.jobs.fulfill_order import ORDERS_FULFILLED_KEY, FulfillOrderJob

    monkeypatch.setenv(
        "DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'amqp.sqlite'}"
    )
    monkeypatch.setenv("QUEUE_CONNECTION", "amqp")
    monkeypatch.setenv("QUEUE_URL", rabbitmq_url)
    from arvel.kernel.bootstrap import bootstrap_app

    from bootstrap.app import create_app

    app = create_app()
    bootstrap_app(
        app
    )  # register providers + config the way the server/worker entrypoints do
    await app.boot()
    try:
        await FulfillOrderJob.dispatch(41)

        manager = app.make("queue")
        worker = asyncio.create_task(manager.work(release_interval=0.2))
        fulfilled = 0
        for _ in range(150):  # up to ~15s for broker round-trip + consume
            fulfilled = await Cache.get(ORDERS_FULFILLED_KEY, 0)
            if fulfilled:
                break
            await asyncio.sleep(0.1)
        worker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker
        assert fulfilled == 1
    finally:
        set_application(None)


async def test_rustfs_s3_disk_roundtrip(
    rustfs_s3: dict[str, str], tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """arvel.filesystem on real RustFS: the kit's s3 disk (env-configured exactly like .env)
    puts/reads/deletes an object."""
    from anyio import to_thread

    from arvel.filesystem import FilesystemManager
    from arvel.kernel import set_application

    bucket = f"arvel-{uuid.uuid4().hex[:10]}"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 's3.sqlite'}")
    monkeypatch.setenv("FILESYSTEM_DISK", "s3")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", rustfs_s3["key"])
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", rustfs_s3["secret"])
    monkeypatch.setenv("AWS_ENDPOINT", rustfs_s3["endpoint"])
    monkeypatch.setenv("AWS_BUCKET", bucket)
    from arvel.kernel.bootstrap import bootstrap_app

    from bootstrap.app import create_app

    app = create_app()
    bootstrap_app(
        app
    )  # register providers + config the way the server/worker entrypoints do
    await app.boot()
    try:
        disk = FilesystemManager(app).disk("s3")
        await to_thread.run_sync(disk.fs.mkdir, bucket)
        await disk.put("smoke/hello.txt", b"hello rustfs")
        assert await disk.exists("smoke/hello.txt") is True
        assert await disk.get("smoke/hello.txt") == b"hello rustfs"
        await disk.delete("smoke/hello.txt")
        assert await disk.exists("smoke/hello.txt") is False
    finally:
        set_application(None)


async def test_meilisearch_indexes_and_searches(
    meilisearch: dict[str, str], tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """arvel.search on real Meilisearch: index the kit catalog (scout:import parity) and search it
    through the model's search surface — the exact driver path the storefront q= uses."""
    from arvel.kernel import set_application

    db_url = f"sqlite+aiosqlite:///{tmp_path / 'meili.sqlite'}"
    await _seed_catalog(db_url)
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("SEARCH_DRIVER", "meilisearch")
    monkeypatch.setenv("MEILISEARCH_URL", meilisearch["url"])
    monkeypatch.setenv("MEILISEARCH_KEY", meilisearch["key"])
    from arvel.kernel.bootstrap import bootstrap_app

    from bootstrap.app import create_app

    app = create_app()
    bootstrap_app(
        app
    )  # register providers + config the way the server/worker entrypoints do
    await app.boot()
    try:
        await Product.make_all_searchable()
        hits: list[Any] = []
        for _ in range(
            60
        ):  # Meilisearch indexes asynchronously (search 404s until the task lands)
            try:
                hits = await Product.search("Aurora")
            except Exception:
                hits = []
            if hits:
                break
            await asyncio.sleep(0.5)
        assert [h.id for h in hits] == [
            1
        ]  # the same hit-id shape the catalog q= path consumes
    finally:
        set_application(None)


def test_keycloak_oidc_admin_me(keycloak_issuer: str, kit_app: Any) -> None:
    """arvel.auth.oidc on real Keycloak: a direct-grant admin token from the imported realm passes
    the OidcGuard (real JWKS, RS256, iss/aud) and JIT-provisions the admin through /api/admin/me."""
    import httpx

    grant = httpx.post(
        f"{keycloak_issuer}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "arvel-admin",
            "username": "admin",
            "password": "admin",
        },
    )
    assert grant.status_code == 200, grant.text
    token = grant.json()["access_token"]

    with kit_app(OIDC_ISSUER=keycloak_issuer) as client:
        me = client.get("/api/admin/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200, me.text
        # a bad token is rejected by the same real-JWKS path
        forged = client.get(
            "/api/admin/me", headers={"Authorization": f"Bearer {token[:-4]}beef"}
        )
        assert forged.status_code == 401


async def test_mailpit_receives_smtp(
    mailpit: dict[str, Any], tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """arvel.mail over real SMTP: the kit's OrderConfirmation mailable is delivered to Mailpit."""
    import httpx

    from arvel.kernel import set_application
    from arvel.support.facades import Mail

    from app.mail.order_confirmation import OrderConfirmation

    monkeypatch.setenv(
        "DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'mail.sqlite'}"
    )
    monkeypatch.setenv("MAIL_MAILER", "smtp")
    monkeypatch.setenv("MAIL_HOST", str(mailpit["host"]))
    monkeypatch.setenv("MAIL_PORT", str(mailpit["smtp_port"]))
    from arvel.kernel.bootstrap import bootstrap_app

    from bootstrap.app import create_app

    app = create_app()
    bootstrap_app(
        app
    )  # register providers + config the way the server/worker entrypoints do
    await app.boot()
    try:
        await Mail.to("smoke@example.com").send(OrderConfirmation(7, 4900))
    finally:
        set_application(None)

    subjects: list[str] = []
    for _ in range(30):
        messages = httpx.get(f"{mailpit['api']}/api/v1/messages").json()["messages"]
        subjects = [m["Subject"] for m in messages]
        if subjects:
            break
        time.sleep(0.5)
    assert "Your order #7 is confirmed" in subjects


def test_dead_service_fails_loudly(kit_app: Any, tmp_path: Any) -> None:
    """The tier must prove tests actually touch their service: pointing the cache at a dead port
    breaks the served cart flow — there is no silent in-memory fallback masking a dead dependency."""
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'dead.sqlite'}"
    asyncio.run(_seed_catalog(db_url))
    with kit_app(
        DATABASE_URL=db_url,
        CACHE_STORE="redis",
        CACHE_URL="redis://127.0.0.1:9/0",  # discard port — nothing listens
    ) as client:
        client.app.debug = False  # surface the failure as a 500, not a raised traceback
        # GET /api/cart computes the subtotal via Cache.remember → must touch the (dead) store
        resp = client.get("/api/cart")
        assert resp.status_code == 500
