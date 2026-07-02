"""S4 — the payment loop on real Postgres: a GUEST pays with the order access token, the signed
webhook lands on the served endpoint, and the order flips to paid — idempotently, with forged
signatures rejected. (The outbound gateway is a MockTransport by design: the PSP is external SaaS,
not infrastructure — PRD non-goal; every shop-side leg is the real served path.)"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from typing import Any

import httpx
import pytest
from litestar.testing import TestClient

from arvel.client import Client

from tests.checkout_helpers import checkout_body
from tests.integration.test_queue_rail import _seed_shop

pytestmark = pytest.mark.integration

_SECRET = "test-secret"


def _gateway(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/charges"):
        return httpx.Response(200, json={"id": "ch_pg_1", "client_secret": "cs_pg_1"})
    return httpx.Response(404, json={"error": "not found"})


def _signed(event: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(event).encode()
    sig = hmac.new(_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return body, {"Content-Type": "application/json", "X-Signature": sig}


def test_guest_token_pay_webhook_paid_on_pg(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_shop(postgres_url))
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from bootstrap.app import create_app

    app = create_app()
    app.instance("http", Client(transport=httpx.MockTransport(_gateway)))
    with TestClient(app=app.as_asgi()) as client:
        cart_token = client.post(
            "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}
        ).json()["cart_token"]
        order = client.post(
            "/api/checkout",
            json=checkout_body(email="guest@example.com"),
            headers={"X-Cart-Token": cart_token},
        ).json()
        order_id, token = order["id"], order["token"]

        # guest pays with the access token
        paid = client.post(
            f"/api/orders/{order_id}/pay", headers={"X-Order-Token": token}
        )
        assert paid.status_code == 201, paid.text

        event = {
            "id": "evt_pg_1",
            "type": "charge.succeeded",
            "data": {"charge_id": "ch_pg_1"},
        }
        body, headers = _signed(event)

        # a forged signature never transitions anything
        forged = client.post(
            "/api/webhooks/payment",
            content=body,
            headers={"Content-Type": "application/json", "X-Signature": "0" * 64},
        )
        assert forged.status_code == 401

        # the genuine webhook pays the order; redelivery is a no-op
        assert (
            client.post("/api/webhooks/payment", content=body, headers=headers).json()[
                "status"
            ]
            == "processed"
        )
        assert (
            client.post("/api/webhooks/payment", content=body, headers=headers).json()[
                "status"
            ]
            == "already_processed"
        )

        shown = client.get(
            f"/api/orders/{order_id}", headers={"X-Order-Token": token}
        ).json()
        assert (shown["status"], shown["payment_status"]) == ("paid", "succeeded")
