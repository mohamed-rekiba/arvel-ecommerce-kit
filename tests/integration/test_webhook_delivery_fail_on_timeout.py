"""K13 — DeliverGatewayWebhook.fail_on_timeout on the REAL amqp+PG rail.

Mirrors the ``test_queue_rail.py`` topology (web boot enqueues, a separate worker boot consumes)
but steers the single ``app.url`` knob across three real delivery targets: a black-hole (accepts
the TCP connection, never responds — the JOB-level ``asyncio.wait_for`` fires), a refusing
listener (accepts, then resets — a plain, non-timeout ``Exception``), and the kit's own app served
live over a real socket. Real worker, real broker, real ``wait_for``, real ``fail_on_timeout=True``
— only duration knobs (``timeout``/``backoff``) are tightened for test speed.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
import struct
import threading
import time
from typing import Any

import httpx
import pytest

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.jobs.deliver_gateway_webhook import DeliverGatewayWebhook

pytestmark = pytest.mark.integration

_CHARGE_BODY = {"amount": 1000, "currency": "usd", "order_id": 1}


async def _migrate(url: str) -> None:
    """Fresh schema per test — the PG container is session-scoped."""
    db = ConnectionResolver({"default": {"url": url}})
    await Migrator(db).drop_all()
    await Migrator(db).run(discover_migrations(["database/migrations"]))
    await db.dispose()


class _CountingServer:
    """A local TCP listener that counts inbound connections.

    ``hold=True`` — a black hole: accepts and never reads/writes, so a delivery hangs until the
    JOB-level ``wait_for(timeout)`` fires (not the client's own read timeout).
    ``hold=False`` — refuses: accepts then immediately resets (abortive close), a real connect-time
    ``Exception`` the worker's generic (non-timeout) retry path handles.
    """

    def __init__(self, *, hold: bool) -> None:
        self._hold = hold
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(16)
        self._sock.settimeout(0.2)
        self.port = self._sock.getsockname()[1]
        self.accepted = 0
        self._held: list[socket.socket] = []
        self._stop = False
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        while not self._stop:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                continue
            self.accepted += 1
            if self._hold:
                self._held.append(conn)  # never read/written — the hang
            else:
                conn.setsockopt(
                    socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)
                )
                conn.close()  # abortive close -> RST, not a graceful FIN

    def close(self) -> None:
        self._stop = True
        self._thread.join(timeout=2)
        for conn in self._held:
            with contextlib.suppress(OSError):
                conn.close()
        self._sock.close()


class _LiveWorkerServer:
    """The kit app served on a real socket AND consuming its own queue — one app, one event loop,
    one background thread. ``arvel``'s ``app()`` accessor is a process-wide global
    (``kernel/globals.py``), not per-instance/thread-local: two independently booted apps racing
    in the same process stomp on it (the second boot's DB engine — bound to ITS loop — becomes
    "the" app, so the first app's request handling starts resolving a DB engine from a different
    loop and blows up). So the delivery target and the worker that drives it have to be the SAME
    booted app here, not a second `_boot_worker_app`-style boot."""

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
            await asyncio.sleep(
                0.02
            )  # ASGI lifespan startup (= app.boot()) has now run
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


async def _boot_worker_app() -> Any:
    """Boot a SEPARATE kit application the way `arvel queue:work` does (worker process topology)."""
    from arvel.kernel.bootstrap import bootstrap_app

    from bootstrap.app import create_app

    app = create_app()
    bootstrap_app(app)
    await app.boot()
    return app


async def _run_worker(timeout: float, until: Any) -> None:
    """Consume from the broker until ``until()`` (an async predicate) is true — or the timeout."""
    app = await _boot_worker_app()
    worker = asyncio.create_task(app.make("queue").work(release_interval=0.2))
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if await until():
            await asyncio.sleep(0.5)  # drain: let any in-flight sibling job finish
            break
        await asyncio.sleep(0.3)
    worker.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await worker


async def _failed_and_queued(url: str) -> tuple[list[Any], int]:
    """Fresh connection (never reused across an ``asyncio.run`` boundary): the ``failed_jobs`` rows
    and how many rows are left in the ``jobs`` (retry-release) table."""
    from arvel.queue import FailedJob
    from arvel.queue.jobs import QueuedJob

    db = ConnectionResolver({"default": {"url": url}})
    FailedJob.set_connection(db)
    QueuedJob.set_connection(db)
    try:
        failed = list(await FailedJob.get())
        queued = list(await QueuedJob.get())
        return failed, len(queued)
    finally:
        FailedJob.set_connection(None)
        QueuedJob.set_connection(None)
        await db.dispose()


def test_timeout_is_terminal_after_exactly_one_attempt(
    postgres_url: str,
    rabbitmq_url: str,
    kit_app: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case 1: the target accepts the connection and hangs — the job's own `wait_for` fires
    (fail_on_timeout=True, the production value), so the delivery is terminal on the FIRST
    attempt: one failed_jobs row, no retry-release row left behind."""
    asyncio.run(_migrate(postgres_url))
    monkeypatch.setattr(
        DeliverGatewayWebhook, "timeout", 1
    )  # duration knob only, for test speed
    blackhole = _CountingServer(hold=True)
    try:
        env = dict(
            DATABASE_URL=postgres_url,
            QUEUE_CONNECTION="amqp",
            QUEUE_URL=rabbitmq_url,
            APP_DEBUG="true",
            APP_URL=f"http://127.0.0.1:{blackhole.port}",
        )
        with kit_app(**env) as client:
            resp = client.post("/api/dev-gateway/charges", json=_CHARGE_BODY)
            assert resp.status_code < 300, resp.text

        async def _one_failed() -> bool:
            from arvel.queue import FailedJob

            return len(await FailedJob.get()) >= 1

        asyncio.run(_run_worker(20.0, _one_failed))

        failed, queued_count = asyncio.run(_failed_and_queued(postgres_url))
        assert len(failed) == 1, failed
        assert "DeliverGatewayWebhook" in failed[0].payload
        assert queued_count == 0  # no retry-release row — never redispatched
        # exactly one TCP connection reached the black hole: one attempt, not a retry loop
        assert blackhole.accepted == 1
    finally:
        blackhole.close()


def test_non_timeout_failure_retries_up_to_tries(
    postgres_url: str,
    rabbitmq_url: str,
    kit_app: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case 2: the target refuses (connect error, a plain Exception, not TimeoutError) — the
    generic retry path runs, unaffected by fail_on_timeout: the worker attempts `tries` times
    before giving up."""
    asyncio.run(_migrate(postgres_url))
    monkeypatch.setattr(
        DeliverGatewayWebhook, "backoff", 0
    )  # duration knob only; tries stays 3
    refuser = _CountingServer(hold=False)
    try:
        env = dict(
            DATABASE_URL=postgres_url,
            QUEUE_CONNECTION="amqp",
            QUEUE_URL=rabbitmq_url,
            APP_DEBUG="true",
            APP_URL=f"http://127.0.0.1:{refuser.port}",
        )
        with kit_app(**env) as client:
            resp = client.post("/api/dev-gateway/charges", json=_CHARGE_BODY)
            assert resp.status_code < 300, resp.text

        async def _one_failed() -> bool:
            from arvel.queue import FailedJob

            return len(await FailedJob.get()) >= 1

        asyncio.run(_run_worker(20.0, _one_failed))

        failed, queued_count = asyncio.run(_failed_and_queued(postgres_url))
        assert len(failed) == 1, failed
        assert queued_count == 0  # exhausted, not stuck mid-retry
        # `tries` (3) separate connections were made before giving up — fail_on_timeout never
        # short-circuited this path (it's a connect error, not a TimeoutError)
        assert refuser.accepted == DeliverGatewayWebhook.tries == 3
    finally:
        refuser.close()


def test_normal_delivery_succeeds(
    postgres_url: str,
    rabbitmq_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case 3: the target is the kit's own app, served live — the signed webhook is delivered,
    the receiver's idempotency ledger records it, and the job completes with zero failed_jobs."""
    asyncio.run(_migrate(postgres_url))
    port = _free_port()
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("QUEUE_CONNECTION", "amqp")
    monkeypatch.setenv("QUEUE_URL", rabbitmq_url)
    monkeypatch.setenv("APP_DEBUG", "true")
    monkeypatch.setenv("APP_URL", f"http://127.0.0.1:{port}")

    live = _LiveWorkerServer(port)
    try:
        resp = httpx.post(
            f"http://127.0.0.1:{port}/api/dev-gateway/charges", json=_CHARGE_BODY
        )
        assert resp.status_code < 300, resp.text

        async def _ledger_count() -> int:
            from app.models.webhook_event import WebhookEvent

            db = ConnectionResolver({"default": {"url": postgres_url}})
            WebhookEvent.set_connection(db)
            try:
                return len(await WebhookEvent.get())
            finally:
                WebhookEvent.set_connection(None)
                await db.dispose()

        deadline = time.time() + 20.0
        count = 0
        while time.time() < deadline:
            count = asyncio.run(_ledger_count())
            if count >= 1:
                break
            time.sleep(0.3)
        assert count == 1

        failed, _ = asyncio.run(_failed_and_queued(postgres_url))
        assert failed == []
    finally:
        live.close()


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port
