"""K9 — the live push, no mocks: a real Postgres + Valkey + RabbitMQ, the served app wrapped by
`BroadcastRelay` (the K9 websocket transport, DR-0066), and a SEPARATE `arvel queue:work` process
(production topology — arvel's global app-per-process design means the worker genuinely must be a
separate OS process, not a second Application booted in-thread) consuming the queued
`StockChanged` broadcast off the real broker. An admin stock adjustment publishes over arvel's own
redis driver; the relay's redis subscription receives it and forwards it to a real websocket
client — the full event → redis → relay → browser-socket path, observed, not asserted.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from tests.rbac_helpers import seed_rbac

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODELS = (Category, Product, ProductVariant)


async def _seed(url: str) -> None:
    from app.models.user import User

    db = ConnectionResolver({"default": {"url": url}})
    await Migrator(db).drop_all()
    await Migrator(db).run(discover_migrations(["database/migrations"]))
    await seed_rbac(db)
    for model in (*_MODELS, User):
        model.set_connection(db)
    try:
        admin = await User.create(
            name="Cat",
            email="catalog@example.com",
            password="secret-catalog",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("catalog-manager")
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        product = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee"}},
            slug="tee",
            price_cents=2000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        await ProductVariant.create(
            product_id=product.id,
            sku="TEE-S",
            name="S",
            price_adjustment_cents=0,
            stock=5,
        )
    finally:
        for model in (*_MODELS, User):
            model.set_connection(None)
        await db.dispose()


def _start_worker(env: dict[str, str]) -> subprocess.Popen[bytes]:
    """`uv run arvel queue:work` as a genuinely separate process — arvel's current-application
    accessor (`arvel.kernel.globals`) is one process-wide reference, so a second Application can't
    safely boot alongside the web app's in the same process."""
    return subprocess.Popen(
        ["uv", "run", "arvel", "queue:work"],
        cwd=_REPO_ROOT,
        env={**os.environ, **env},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_stock_changed_travels_redis_to_the_relay_to_a_real_websocket(
    postgres_url: str,
    valkey_url: str,
    rabbitmq_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from litestar.testing import TestClient

    from app.realtime.broadcast_relay import BroadcastRelay

    env = {
        "DATABASE_URL": postgres_url,
        "REDIS_URL": valkey_url,
        "BROADCAST_CONNECTION": "redis",
        "QUEUE_CONNECTION": "amqp",
        "QUEUE_URL": rabbitmq_url,
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    asyncio.run(_seed(postgres_url))

    from bootstrap.app import create_app

    app: Any = create_app()
    asgi = BroadcastRelay(app, app.as_asgi())

    worker = _start_worker(env)
    try:
        time.sleep(
            3.0
        )  # let the worker connect to the broker before anything is published
        with TestClient(app=asgi) as client:
            admin = client.post(
                "/api/login",
                json={"email": "catalog@example.com", "password": "secret-catalog"},
            ).json()["token"]
            headers = {"Authorization": f"Bearer {admin}"}

            with client.websocket_connect("/ws") as ws:
                connected = ws.receive_json()
                assert connected["event"] == "connected"
                ws.send_json({"event": "subscribe", "channel": "stock.1"})
                time.sleep(
                    0.5
                )  # let the relay's redis SUBSCRIBE land before we publish

                resp = client.post(
                    "/api/admin/products/1/variants/1/stock",
                    json={"set": 7},
                    headers=headers,
                )
                assert resp.status_code == 200, resp.text

                frame = ws.receive_json()
                assert frame == {
                    "event": "StockChanged",
                    "data": {"variant_id": 1, "stock": 7, "in_stock": True},
                }
    finally:
        worker.terminate()
        try:
            worker.wait(timeout=10)
        except subprocess.TimeoutExpired:
            worker.kill()
