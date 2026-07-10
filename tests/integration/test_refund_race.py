"""K15 — refunds on REAL infra: PG + RabbitMQ + the kit's own dev-gateway, served live over a real
socket. Proves what only real infra can prove: a genuine two-connection race on guard 1 (the
`FOR UPDATE` transition + partial-unique index), and the real async queue -> dev-gateway ->
`charge.refunded` webhook round trip (restock-exactly-once, then redelivery idempotency, guard 2).

The state-rejection matrix (PENDING/COD/already-refunded -> 422/409), the SHIPPED-return
no-restock case, forged-signature rejection, and authz are all infra-independent — they don't
depend on genuine concurrency or the real queue — so they're proven once, thoroughly, at the unit
tier (tests/test_refunds.py) through the same served path with a mocked gateway transport; re-
running them here would only pay the (expensive) container cost twice for the same evidence.

Topology mirrors test_webhook_delivery_fail_on_timeout.py: arvel's `app()` accessor is a
process-wide global, so the dev-gateway target and the worker that drains its queued webhook must
be the SAME booted app, not two boots racing on one event loop — hence `_LiveWorkerServer`.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import json
import os
import socket
import threading
import time

import httpx
import pytest

from arvel.database import ConnectionResolver

from tests.checkout_helpers import checkout_body
from tests.integration.test_queue_rail import _seed_shop

pytestmark = pytest.mark.integration

_WEBHOOK_SECRET = os.environ["PAYMENT_GATEWAY_SECRET"]


class _LiveWorkerServer:
    """The kit app served on a real socket AND consuming its own queue — one app, one event loop,
    one background thread (see test_webhook_delivery_fail_on_timeout.py for why this can't be two
    separate boots)."""

    def __init__(self, port: int) -> None:
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(port,), daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=10):
            raise RuntimeError("live server never became ready")

    def _run(self, port: int) -> None:
        asyncio.run(self._main(port))

    async def _main(self, port: int) -> None:
        import uvicorn

        from bootstrap.app import create_app

        config = uvicorn.Config(
            create_app().as_asgi(), host="127.0.0.1", port=port, log_level="warning"
        )
        server = uvicorn.Server(config)
        serve_task = asyncio.create_task(server.serve())
        while not server.started:
            await asyncio.sleep(0.02)
        from arvel.kernel import app as kernel_app

        worker_task = asyncio.create_task(
            kernel_app().make("queue").work(release_interval=0.2)
        )
        self._ready.set()
        while not self._stop.is_set():
            await asyncio.sleep(0.1)
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task
        server.should_exit = True
        await serve_task

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=10)


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _login(base: str, email: str, password: str) -> dict[str, str]:
    token = httpx.post(
        f"{base}/api/login", json={"email": email, "password": password}, timeout=10
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


async def _refund_row_count(url: str, order_id: int) -> int:
    from app.models.refund import Refund

    db = ConnectionResolver({"default": {"url": url}})
    Refund.set_connection(db)
    try:
        return len(await Refund.where("order_id", order_id).get())
    finally:
        Refund.set_connection(None)
        await db.dispose()


async def _last_refund_event_id(url: str) -> str:
    from app.models.webhook_event import WebhookEvent

    db = ConnectionResolver({"default": {"url": url}})
    WebhookEvent.set_connection(db)
    try:
        event = (
            await WebhookEvent.where("type", "charge.refunded")
            .order_by("id", "desc")
            .first()
        )
        assert event is not None
        return str(event.event_id)
    finally:
        WebhookEvent.set_connection(None)
        await db.dispose()


def test_concurrent_paid_cancels_refund_exactly_once_then_redelivery_is_idempotent(
    postgres_url: str,
    rabbitmq_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The full live loop: pay -> PAID; two SIMULTANEOUS cancels -> exactly one REFUND_PENDING (the
    other 409, guard 1) and exactly one reverse call ever reaches the dev gateway; the queued
    charge.refunded lands -> REFUNDED + stock restocked EXACTLY once; a third cancel attempt on the
    now-REFUNDED order -> 409 (guard 3); redelivering the SAME webhook event -> already_processed,
    stock unchanged (guard 2)."""
    asyncio.run(_seed_shop(postgres_url))
    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("QUEUE_CONNECTION", "amqp")
    monkeypatch.setenv("QUEUE_URL", rabbitmq_url)
    monkeypatch.setenv("APP_DEBUG", "true")
    monkeypatch.setenv("APP_URL", base)
    # the built-in dev PSP stub, on the SAME live app — the real reverse-call round trip, not a mock
    monkeypatch.setenv("PAYMENT_GATEWAY_URL", f"{base}/api/dev-gateway")

    live = _LiveWorkerServer(port)
    try:
        customer = _login(base, "cara@example.com", "secret-cara")
        httpx.post(
            f"{base}/api/cart/items",
            json={"product_variant_id": 1, "quantity": 5},
            headers=customer,
            timeout=10,
        )
        order_id = httpx.post(
            f"{base}/api/checkout", json=checkout_body(), headers=customer, timeout=10
        ).json()["id"]
        httpx.post(f"{base}/api/orders/{order_id}/pay", headers=customer, timeout=10)

        def _status() -> str:
            return httpx.get(
                f"{base}/api/orders/{order_id}", headers=customer, timeout=10
            ).json()["status"]

        deadline = time.time() + 20.0
        while time.time() < deadline and _status() != "paid":
            time.sleep(0.3)
        assert _status() == "paid", "order never reached PAID"

        # stock went 100 -> 95 at checkout
        results: list[int] = []

        def _cancel() -> None:
            results.append(
                httpx.post(
                    f"{base}/api/orders/{order_id}/cancel", headers=customer, timeout=10
                ).status_code
            )

        threads = [threading.Thread(target=_cancel) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # exactly one winner (-> REFUND_PENDING); the loser hit guard 1 (can_transition under lock)
        assert sorted(results) == [200, 409], results

        deadline = time.time() + 20.0
        while time.time() < deadline and _status() != "refunded":
            time.sleep(0.3)
        assert _status() == "refunded"

        product = httpx.get(f"{base}/api/products/tee", timeout=10).json()
        assert (
            product["variants"][0]["stock"] == 100
        )  # 95 + 5 — exactly one restock, not 105

        # guard 1's DB-level backstop: only ONE Refund row was ever created for this order, so
        # only ONE reverse call was ever issued (Refund.create always immediately precedes it)
        assert asyncio.run(_refund_row_count(postgres_url, order_id)) == 1

        # a THIRD attempt, now against a terminal REFUNDED order -> guard 3 on the INITIATION side
        # (can_transition(REFUNDED, REFUND_PENDING) is False)
        third = httpx.post(
            f"{base}/api/orders/{order_id}/cancel", headers=customer, timeout=10
        )
        assert third.status_code in (409, 422)
        assert (
            asyncio.run(_refund_row_count(postgres_url, order_id)) == 1
        )  # still just the one

        # redeliver the EXACT SAME webhook event the queue already delivered (same event_id,
        # bypassing the queue this time) -> guard 2 (event_id ledger): already_processed, no
        # second restock. Read the real event_id back from the ledger — it's a random uuid minted
        # by DeliverGatewayWebhook.dispatch, not something the test controls.
        event_id = asyncio.run(_last_refund_event_id(postgres_url))
        detail = httpx.get(
            f"{base}/api/admin/orders/{order_id}",
            headers=_login(base, "admin@example.com", "secret-admin"),
            timeout=10,
        ).json()
        succeeded_refund = next(
            r for r in detail["refunds"] if r["status"] == "succeeded"
        )
        event = {
            "id": event_id,
            "type": "charge.refunded",
            "data": {"charge_id": succeeded_refund["gateway_charge_id"]},
        }
        body = json.dumps(event).encode()
        signature = hmac.new(_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        redelivered = httpx.post(
            f"{base}/api/webhooks/payment",
            content=body,
            headers={"Content-Type": "application/json", "X-Signature": signature},
            timeout=10,
        )
        assert redelivered.status_code < 300
        assert redelivered.json()["status"] == "already_processed"
        assert (
            httpx.get(f"{base}/api/products/tee", timeout=10).json()["variants"][0][
                "stock"
            ]
            == 100
        )  # unchanged — not 105
        assert _status() == "refunded"
    finally:
        live.close()
