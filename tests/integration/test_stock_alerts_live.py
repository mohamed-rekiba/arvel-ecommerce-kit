"""S17 — the restock fan-out on real infra: N subscribers → N queued jobs consumed by a real
worker off RabbitMQ → N mails in Mailpit + N database notifications on PG."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from tests.integration.test_queue_rail import (
    _login,
    _mailpit_subjects,
    _place_and_ship,
    _run_worker,
    _seed_shop,
)

pytestmark = pytest.mark.integration


def test_fanout_rides_the_worker(
    postgres_url: str,
    rabbitmq_url: str,
    mailpit: dict[str, Any],
    kit_app: Any,
) -> None:
    asyncio.run(_seed_shop(postgres_url))

    async def _sell_out() -> None:
        import sqlalchemy as sa
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(postgres_url)
        async with engine.begin() as conn:
            await conn.execute(sa.text("UPDATE product_variants SET stock = 0"))
        await engine.dispose()

    asyncio.run(_sell_out())
    env = dict(
        DATABASE_URL=postgres_url,
        QUEUE_CONNECTION="amqp",
        QUEUE_URL=rabbitmq_url,
        MAIL_MAILER="smtp",
        MAIL_HOST=str(mailpit["host"]),
        MAIL_PORT=str(mailpit["smtp_port"]),
    )
    with kit_app(**env) as client:
        # two subscribers on the sold-out variant
        subscribers = []
        for name, email in (("Cara", "cara@example.com"),):
            token = client.post(
                "/api/login", json={"email": email, "password": "secret-cara"}
            ).json()["token"]
            subscribers.append({"Authorization": f"Bearer {token}"})
        reg = client.post(
            "/api/register",
            json={
                "name": "Noah",
                "email": "noah@example.com",
                "password": "supersecret",
            },
        ).json()["token"]
        subscribers.append({"Authorization": f"Bearer {reg}"})
        for headers in subscribers:
            assert (
                client.post("/api/variants/1/stock-alert", headers=headers).status_code
                == 200
            )

        # the admin restocks 0→6 — the fan-out is QUEUED, not inline
        admin = {
            "Authorization": f"Bearer {client.post('/api/login', json={'email': 'admin@example.com', 'password': 'secret-admin'}).json()['token']}"
        }
        client.post(
            "/api/admin/products/1/variants/1/stock",
            json={"set": 6, "reason": "container arrived"},
            headers=admin,
        )
        # nothing delivered yet — the jobs sit on the broker
        for headers in subscribers:
            assert client.get("/api/notifications", headers=headers).json() == []

    async def _delivered() -> bool:
        subjects = [
            m["Subject"]
            for m in httpx.get(f"{mailpit['api']}/api/v1/messages").json()["messages"]
        ]
        return sum("Back in stock" in s for s in subjects) >= 2

    asyncio.run(_run_worker(30.0, until=_delivered))

    with kit_app(**env) as client:
        for email, password in (
            ("cara@example.com", "secret-cara"),
            ("noah@example.com", "supersecret"),
        ):
            token = client.post(
                "/api/login", json={"email": email, "password": password}
            ).json()["token"]
            notes = client.get(
                "/api/notifications", headers={"Authorization": f"Bearer {token}"}
            ).json()
            assert [n["type"] for n in notes] == ["BackInStockNotification"]


def _mailpit_count(api: str, *, to: str, subject_contains: str) -> int:
    """Delivered-mail count for one recipient matching a subject substring — Mailpit's list
    endpoint already carries `To` per message, no per-message fetch needed."""
    messages = httpx.get(f"{api}/api/v1/messages").json()["messages"]
    return sum(
        subject_contains in m["Subject"]
        and any(t.get("Address") == to for t in m.get("To") or [])
        for m in messages
    )


def test_rate_limit_caps_back_in_stock_per_user_and_leaves_shipped_unthrottled(
    postgres_url: str,
    rabbitmq_url: str,
    mailpit: dict[str, Any],
    kit_app: Any,
) -> None:
    """K11/E15 (DR-0059): a variant flapping in and out of stock re-fires the restock fan-out on
    every cycle. Within the rate-limit's window, each subscriber's mailbox caps at ONE back-in-stock
    mail no matter how many times it flapped — and Cara hitting her cap never touches Noah's (the
    per-recipient key DR-0059 makes reachable; before it, the only expressible key was per-product,
    a SHARED throttle). An order-shipped notification fired in the same burst is untouched — it
    declares no middleware, so it delivers every time."""
    # mailpit is a SESSION-scoped fixture (one throwaway inbox for the whole test run) — an
    # earlier test in this same file (test_fanout_rides_the_worker) sends its own "Back in stock"
    # mail to these exact seeded addresses (cara@example.com/noah@example.com), which would
    # otherwise double-count against this test's exact-1-per-window assertion. Clear it first so
    # only messages THIS test causes are on the wire.
    httpx.delete(f"{mailpit['api']}/api/v1/messages")
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
        order_id = _place_and_ship(
            client
        )  # the unthrottled control, fired once in this same run

        admin = _login(client, "admin@example.com", "secret-admin")
        cara = _login(client, "cara@example.com", "secret-cara")
        noah_token = client.post(
            "/api/register",
            json={
                "name": "Noah",
                "email": "noah@example.com",
                "password": "supersecret",
            },
        ).json()["token"]
        noah = {"Authorization": f"Bearer {noah_token}"}

        # 3 flaps within the window: sell out -> both re-subscribe (subscribing needs stock == 0)
        # -> restock (the 0->positive edge fires the fan-out, consuming the alert one-shot).
        for _ in range(3):
            client.post(
                "/api/admin/products/1/variants/1/stock",
                json={"set": 0, "reason": "flap"},
                headers=admin,
            )
            for headers in (cara, noah):
                assert (
                    client.post(
                        "/api/variants/1/stock-alert", headers=headers
                    ).status_code
                    == 200
                )
            client.post(
                "/api/admin/products/1/variants/1/stock",
                json={"set": 5, "reason": "flap"},
                headers=admin,
            )

    async def _drained() -> bool:
        subjects = _mailpit_subjects(mailpit["api"])
        return (
            sum("Back in stock" in s for s in subjects) >= 2
            and f"Your order #{order_id} has shipped" in subjects
        )

    asyncio.run(_run_worker(40.0, until=_drained))

    cara_count = _mailpit_count(
        mailpit["api"], to="cara@example.com", subject_contains="Back in stock"
    )
    noah_count = _mailpit_count(
        mailpit["api"], to="noah@example.com", subject_contains="Back in stock"
    )
    shipped_count = _mailpit_subjects(mailpit["api"]).count(
        f"Your order #{order_id} has shipped"
    )

    # per-window cap: 3 flaps x 2 subscribers queued 3 back-in-stock jobs each, but max_attempts=1
    # lets only the FIRST through per recipient — the other 2 are released back onto the queue for
    # a later window, not dropped (this test doesn't wait out the 300s decay to prove that half;
    # it proves the window cap and the per-recipient independence DR-0059 enables).
    assert cara_count == 1
    assert (
        noah_count == 1
    )  # independent of Cara's cap — distinct keys, distinct counters
    assert (
        shipped_count == 1
    )  # no middleware declared -> delivered every time, never released
