"""S17 — the restock fan-out on real infra: N subscribers → N queued jobs consumed by a real
worker off RabbitMQ → N mails in Mailpit + N database notifications on PG."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from tests.integration.test_queue_rail import _run_worker, _seed_shop

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
