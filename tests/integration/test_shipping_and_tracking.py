"""K16 — shipping rate resolved from a selectable method (standard/express), on real Postgres,
plus the ship-transition tracking-number requirement on real Postgres + RabbitMQ + Mailpit.

Same cart, two methods: standard vs express charge DIFFERENT server-computed shipping (DR-0064).
A client-injected rate/amount is proven to have no effect — the server-resolved method rate always
wins. An unknown OR a real seeded-but-inactive method 422s (not a silent fallback, not a 500). The
ship transition (SHIPPED) 422s without a tracking number and stores/surfaces it (order detail DTO
+ the delivered mail body) once supplied — the proven order-shipped mail rail keeps delivering.
Every assertion reads the PERSISTED order row (or the real Mailpit message), not just the DTO.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from tests.checkout_helpers import checkout_body
from tests.integration.test_queue_rail import (
    _login,
    _mailpit_subjects,
    _run_worker,
    _seed_shop,
)

pytestmark = pytest.mark.integration


async def _seed_extra_methods(url: str) -> None:
    """Beside the `standard` row `_seed_shop` already creates: `express` (active, a different
    rate) and `legacy` (a REAL seeded row with active=False) — so the inactive-method case proves
    against real data, not a fabricated one."""
    from arvel.database import ConnectionResolver

    from app.models.shipping_method import ShippingMethod

    db = ConnectionResolver({"default": {"url": url}})
    ShippingMethod.set_connection(db)
    try:
        await ShippingMethod.create(
            code="express", name="Express", rate_cents=1500, active=True, sort=1
        )
        await ShippingMethod.create(
            code="legacy", name="Legacy Post", rate_cents=300, active=False, sort=2
        )
    finally:
        ShippingMethod.set_connection(None)
        await db.dispose()


async def _order_row(url: str, order_id: int) -> dict[str, Any]:
    """Read the order straight off Postgres — the acceptance is on the persisted row, not just
    the response DTO."""
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                sa.text(
                    "SELECT shipping_cents, shipping_method, tracking_number, total_cents, status "
                    "FROM orders WHERE id = :id"
                ),
                {"id": order_id},
            )
            return dict(result.mappings().one())
    finally:
        await engine.dispose()


def _mailpit_message_html(api: str, subject: str) -> str:
    """The HTML body of the (unique) Mailpit message with the given subject."""
    messages = httpx.get(f"{api}/api/v1/messages").json()["messages"]
    match = next(m for m in messages if m["Subject"] == subject)
    return httpx.get(f"{api}/api/v1/message/{match['ID']}").json()["HTML"]


def _checkout(client: Any, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=headers,
    )
    body = checkout_body()
    body.update(overrides)
    placed = client.post("/api/checkout", json=body, headers=headers)
    assert placed.status_code == 201, placed.text
    return placed.json()


def test_shipping_rate_by_method_and_unavailable_method_422s(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_shop(postgres_url))
    asyncio.run(_seed_extra_methods(postgres_url))
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from litestar.testing import TestClient

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as client:
        customer = _login(client, "cara@example.com", "secret-cara")

        # A — standard: the seeded 500c rate
        std = _checkout(client, customer, shipping_method="standard")
        std_row = asyncio.run(_order_row(postgres_url, std["id"]))
        assert std_row["shipping_method"] == "standard"
        assert std_row["shipping_cents"] == 500
        assert std_row["total_cents"] == std["subtotal_cents"] + 500 + std["tax_cents"]

        # B — express: the seeded 1500c rate — DIFFERENT charge, same cart, server-computed
        exp = _checkout(client, customer, shipping_method="express")
        exp_row = asyncio.run(_order_row(postgres_url, exp["id"]))
        assert exp_row["shipping_method"] == "express"
        assert exp_row["shipping_cents"] == 1500
        assert exp_row["shipping_cents"] != std_row["shipping_cents"]

        # C — a crafted payload carrying a shipping rate is IGNORED: standard still charges 500c
        injected = _checkout(
            client,
            customer,
            shipping_method="standard",
            shipping_cents=1,
            rate=99999,
        )
        injected_row = asyncio.run(_order_row(postgres_url, injected["id"]))
        assert (
            injected_row["shipping_cents"] == 500
        )  # the server rate, not the injected one

        # D — an unknown method -> 422 (field error), not a 500, and no order created
        before_count = len(client.get("/api/orders", headers=customer).json())
        client.post(
            "/api/cart/items",
            json={"product_variant_id": 1, "quantity": 1},
            headers=customer,
        )
        unknown = client.post(
            "/api/checkout",
            json={**checkout_body(), "shipping_method": "overnight"},
            headers=customer,
        )
        assert unknown.status_code == 422
        assert "shipping_method" in unknown.json()["errors"]
        assert len(client.get("/api/orders", headers=customer).json()) == before_count

        # E — a REAL seeded but active=False method -> 422 too (not only a missing one)
        client.post(
            "/api/cart/items",
            json={"product_variant_id": 1, "quantity": 1},
            headers=customer,
        )
        inactive = client.post(
            "/api/checkout",
            json={**checkout_body(), "shipping_method": "legacy"},
            headers=customer,
        )
        assert inactive.status_code == 422
        assert "shipping_method" in inactive.json()["errors"]


def test_ship_transition_requires_and_surfaces_tracking(
    postgres_url: str,
    rabbitmq_url: str,
    mailpit: dict[str, Any],
    kit_app: Any,
    monkeypatch: pytest.MonkeyPatch,
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
        customer = _login(client, "cara@example.com", "secret-cara")
        admin = _login(client, "admin@example.com", "secret-admin")
        order = _checkout(client, customer)
        order_id = order["id"]
        client.post(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "paid"},
            headers=admin,
        )

        # F — shipped WITHOUT a tracking number -> 422; the order stays not-shipped
        blank = client.post(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "shipped"},
            headers=admin,
        )
        assert blank.status_code == 422
        assert "tracking_number" in blank.json()["errors"]
        row = asyncio.run(_order_row(postgres_url, order_id))
        assert row["status"] == "paid"
        assert row["tracking_number"] is None

        # G — shipped WITH a tracking number -> 200, persisted
        tracking = "1Z999AA10123456784"
        shipped = client.post(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "shipped", "tracking_number": tracking},
            headers=admin,
        )
        assert shipped.status_code == 200, shipped.text
        row = asyncio.run(_order_row(postgres_url, order_id))
        assert row["status"] == "shipped"
        assert row["tracking_number"] == tracking

        # H(a) — tracking surfaced in the order-detail DTO
        detail = client.get(f"/api/orders/{order_id}", headers=customer).json()
        assert detail["tracking_number"] == tracking

    # I — the proven rail still delivers (database + mail channels) — worker consumes the queue
    async def _delivered() -> bool:
        return f"Your order #{order_id} has shipped" in _mailpit_subjects(
            mailpit["api"]
        )

    asyncio.run(_run_worker(30.0, until=_delivered))

    with kit_app(**env) as client:
        customer = _login(client, "cara@example.com", "secret-cara")
        notes = client.get("/api/notifications", headers=customer).json()
        assert [n["type"] for n in notes] == ["OrderShippedNotification"]  # db channel

    # H(b) — the delivered mail BODY contains the tracking number, not just the subject
    html = _mailpit_message_html(mailpit["api"], f"Your order #{order_id} has shipped")
    assert tracking in html
