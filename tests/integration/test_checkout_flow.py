"""S3 — checkout on real infra: the persisted money breakdown on PG and the GUEST confirmation
mail delivered over real SMTP (the audit's A3: guests could never receive order mail)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from tests.checkout_helpers import checkout_body
from tests.integration.test_queue_rail import (
    _mailpit_subjects,
    _run_worker,
    _seed_shop,
)

pytestmark = pytest.mark.integration


def test_guest_checkout_persists_breakdown_and_mails_the_guest(
    postgres_url: str,
    rabbitmq_url: str,
    mailpit: dict[str, Any],
    kit_app: Any,
) -> None:
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
        token = client.post(
            "/api/cart/items", json={"product_variant_id": 1, "quantity": 2}
        ).json()["cart_token"]
        placed = client.post(
            "/api/checkout",
            json=checkout_body(email="guest@example.com"),
            headers={"X-Cart-Token": token},
        )
        assert placed.status_code == 201, placed.text
        order = placed.json()
        # server-computed breakdown persisted on PG: 2×2000 + 500 shipping + 10% tax
        assert (
            order["subtotal_cents"],
            order["shipping_cents"],
            order["tax_cents"],
            order["total_cents"],
        ) == (4000, 500, 400, 4900)
        assert order["contact_email"] == "guest@example.com"
        assert order["address"]["country"] == "US"
        order_id = order["id"]

    async def _delivered() -> bool:
        return f"Your order #{order_id} is confirmed" in _mailpit_subjects(
            mailpit["api"]
        )

    asyncio.run(_run_worker(30.0, until=_delivered))
    assert f"Your order #{order_id} is confirmed" in _mailpit_subjects(mailpit["api"])
