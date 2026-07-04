"""S2 — the queued-notification delivery rail on REAL infra: PG + RabbitMQ + Mailpit.

Production topology, faithfully: the web process (TestClient over the kit boot) enqueues onto the
AMQP broker; a separate worker boot consumes and delivers. Proves (1) a SHIPPED transition commits
without waiting on SMTP, (2) the database + mail channels ride SEPARATE jobs, (3) an SMTP outage
lands the mail job on the failed-jobs rail without touching the stored notification, and (4)
`queue:retry` semantics (FailedJob.retry) deliver once SMTP is back.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Any

import httpx
import pytest

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from tests.rbac_helpers import seed_rbac
from tests.checkout_helpers import checkout_body

pytestmark = pytest.mark.integration

_MODELS = (User, Category, Product, ProductVariant)


async def _seed_shop(url: str) -> None:
    """Migrate + seed a customer, an RBAC admin, and one purchasable product."""
    db = ConnectionResolver({"default": {"url": url}})
    migrator = Migrator(db)
    await (
        migrator.drop_all()
    )  # the PG container is session-scoped; each test starts clean
    await migrator.run(discover_migrations(["database/migrations"]))
    await seed_rbac(db)
    for model in _MODELS:
        model.set_connection(db)
    try:
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        admin = await User.create(
            name="Ada",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("super-admin")
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        product = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee", "description": "A tee."}},
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
            stock=100,
        )
        # on PG the retrievable_* views are MATERIALIZED — recompute so storefront reads see the seed
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
        for model in _MODELS:
            model.set_connection(None)
        await db.dispose()


def _login(client: Any, email: str, password: str) -> dict[str, str]:
    token = client.post(
        "/api/login", json={"email": email, "password": password}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _place_and_ship(client: Any) -> int:
    """Customer checks out; admin advances pending→paid→shipped. Returns the order id."""
    customer = _login(client, "cara@example.com", "secret-cara")
    admin = _login(client, "admin@example.com", "secret-admin")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=customer,
    )
    order_id = int(
        client.post("/api/checkout", json=checkout_body(), headers=customer).json()[
            "id"
        ]
    )
    for nxt in ("paid", "shipped"):
        resp = client.post(
            f"/api/admin/orders/{order_id}/status", json={"status": nxt}, headers=admin
        )
        assert resp.status_code == 200, resp.text
    return order_id


async def _boot_worker_app() -> Any:
    """Boot a SEPARATE kit application the way `arvel queue:work` does (worker process topology)."""
    from arvel.kernel.bootstrap import bootstrap_app

    from bootstrap.app import create_app

    app = create_app()
    bootstrap_app(app)
    await app.boot()
    return app


async def _run_worker(timeout: float, until: Any = None) -> None:
    """Consume from the broker until ``until()`` (an async predicate) is true — or the timeout —
    then stop. Cancelling on a predicate (not a blind sleep) never kills a delivery mid-send."""
    app = await _boot_worker_app()
    worker = asyncio.create_task(app.make("queue").work(release_interval=0.2))
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if until is not None and await until():
            await asyncio.sleep(
                1.0
            )  # drain: let any in-flight sibling job finish its send
            break
        await asyncio.sleep(0.5)
    worker.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await worker


def _mailpit_subjects(api: str) -> list[str]:
    return [
        m["Subject"] for m in httpx.get(f"{api}/api/v1/messages").json()["messages"]
    ]


def test_shipped_notification_rides_the_worker(
    postgres_url: str,
    rabbitmq_url: str,
    mailpit: dict[str, Any],
    kit_app: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: ship → 200 immediately (nothing sent yet) → worker consumes off RabbitMQ →
    the database notification appears in the account API and the mail lands in Mailpit."""
    asyncio.run(_seed_shop(postgres_url))
    env = dict(
        DATABASE_URL=postgres_url,
        QUEUE_CONNECTION="amqp",
        QUEUE_URL=rabbitmq_url,
        MAIL_MAILER="smtp",
        MAIL_HOST=str(mailpit["host"]),
        MAIL_PORT=str(mailpit["smtp_port"]),
    )
    with kit_app(**env) as client:
        order_id = _place_and_ship(client)
        customer = _login(client, "cara@example.com", "secret-cara")
        # queued, not sent inline: no stored notification until a worker runs
        assert client.get("/api/notifications", headers=customer).json() == []

    async def _delivered() -> bool:
        return f"Your order #{order_id} has shipped" in _mailpit_subjects(
            mailpit["api"]
        )

    asyncio.run(_run_worker(30.0, until=_delivered))

    with kit_app(**env) as client:
        customer = _login(client, "cara@example.com", "secret-cara")
        notes = client.get("/api/notifications", headers=customer).json()
        assert [n["type"] for n in notes] == ["OrderShippedNotification"]
        assert f"#{order_id}" in notes[0]["message"]
    assert f"Your order #{order_id} has shipped" in _mailpit_subjects(mailpit["api"])


def test_smtp_outage_fails_only_the_mail_job_and_retry_delivers(
    postgres_url: str,
    rabbitmq_url: str,
    mailpit: dict[str, Any],
    kit_app: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failure path: with SMTP dead, shipping still commits (200); the worker stores the database
    notification (its own job) while the mail job exhausts retries onto the failed-jobs rail —
    exactly ONE stored notification, no double-store. With SMTP back, retrying the failed job
    (queue:retry semantics) delivers the mail."""
    from arvel.mail import SendQueuedMailable
    from arvel.notifications import SendQueuedNotification

    for job_cls in (SendQueuedNotification, SendQueuedMailable):
        monkeypatch.setattr(job_cls, "tries", 2)
        monkeypatch.setattr(job_cls, "backoff", 0)

    asyncio.run(_seed_shop(postgres_url))
    dead_env = dict(
        DATABASE_URL=postgres_url,
        QUEUE_CONNECTION="amqp",
        QUEUE_URL=rabbitmq_url,
        MAIL_MAILER="smtp",
        MAIL_HOST="127.0.0.1",
        MAIL_PORT="9",  # discard port — SMTP is down
    )
    with kit_app(**dead_env) as client:
        order_id = _place_and_ship(
            client
        )  # 200s prove the transition never waits on SMTP

    async def _mail_jobs_failed() -> bool:
        from arvel.queue import FailedJob

        return (
            len(await FailedJob.get()) >= 2
        )  # OrderConfirmation mail + OrderShipped mail

    asyncio.run(_run_worker(30.0, until=_mail_jobs_failed))

    with kit_app(**dead_env) as client:
        customer = _login(client, "cara@example.com", "secret-cara")
        notes = client.get("/api/notifications", headers=customer).json()
        # the database channel delivered exactly once, isolated from the mail failure
        assert [n["type"] for n in notes] == ["OrderShippedNotification"]

    async def _failed_jobs_then_retry() -> tuple[int, int]:
        """Count failed jobs, then retry them under a fixed (live-SMTP) config — the operator's
        queue:retry after restoring the mailer."""
        from arvel.queue import FailedJob

        app = await _boot_worker_app()
        mail_cfg = app.make("config").get("mail")
        mail_cfg["smtp"]["host"] = str(
            mailpit["host"]
        )  # SMTP restored (the operator fixed it)
        mail_cfg["smtp"]["port"] = int(mailpit["smtp_port"])
        failed = await FailedJob.get()
        for row in failed:
            await row.retry()
        worker = asyncio.create_task(app.make("queue").work(release_interval=0.2))
        deadline = asyncio.get_event_loop().time() + 20
        while asyncio.get_event_loop().time() < deadline:
            if f"Your order #{order_id} has shipped" in _mailpit_subjects(
                mailpit["api"]
            ):
                await asyncio.sleep(1.0)  # drain the sibling delivery
                break
            await asyncio.sleep(0.5)
        worker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker
        remaining = len(await FailedJob.get())
        return len(failed), remaining

    failed_count, remaining = asyncio.run(_failed_jobs_then_retry())
    assert (
        failed_count == 2
    )  # the two MAIL jobs (confirmation + shipped) — never the db channel
    assert remaining == 0  # retry consumed the records

    deadline = time.time() + 10
    while time.time() < deadline:
        if f"Your order #{order_id} has shipped" in _mailpit_subjects(mailpit["api"]):
            break
        time.sleep(0.5)
    assert f"Your order #{order_id} has shipped" in _mailpit_subjects(mailpit["api"])
