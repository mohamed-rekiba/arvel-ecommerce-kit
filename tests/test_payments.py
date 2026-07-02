"""Payments — gateway charge via the Http client (faked with a MockTransport) + idempotent webhook
processing, through the real served path. A redelivered webhook is processed exactly once.
"""

import asyncio
import hashlib
import hmac
import json

import httpx
import pytest
from litestar.testing import TestClient

from arvel.client import Client
from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from tests.checkout_helpers import checkout_body

_WEBHOOK_SECRET = "test-secret"  # config/services.py default (PAYMENT_GATEWAY_SECRET)


def _post_webhook(client, event: dict, *, sign: bool = True):
    """POST a gateway webhook, signing the exact raw body with the gateway HMAC secret by default."""
    body = json.dumps(event).encode()
    headers = {"Content-Type": "application/json"}
    if sign:
        headers["X-Signature"] = hmac.new(
            _WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
    return client.post("/api/webhooks/payment", content=body, headers=headers)


def _gateway_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/charges":
        return httpx.Response(
            200, json={"id": "ch_test_123", "client_secret": "cs_test_abc"}
        )
    return httpx.Response(404, json={"error": "not found"})


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'payments.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(db)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts"
        )
        p = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee"}},
            slug="tee",
            price_cents=2000,
            currency="USD",
            status=ProductStatus.ACTIVE,
        )
        await ProductVariant.create(
            product_id=p.id, sku="TEE-S", name="S", price_adjustment_cents=0, stock=100
        )
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())

    from bootstrap.app import create_app

    app = create_app()
    # fake the payment gateway by binding an Http client with a MockTransport (no real network)
    app.instance("http", Client(transport=httpx.MockTransport(_gateway_handler)))
    with TestClient(app=app.as_asgi()) as test_client:
        yield test_client


def _auth(client) -> dict:
    token = client.post(
        "/api/login", json={"email": "cara@example.com", "password": "secret-cara"}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _place_order(client, headers) -> int:
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 2},
        headers=headers,
    )
    return client.post("/api/checkout", json=checkout_body(), headers=headers).json()["id"]


def test_pay_calls_the_gateway_and_records_a_payment(client) -> None:
    headers = _auth(client)
    order_id = _place_order(client, headers)
    resp = client.post(f"/api/orders/{order_id}/pay", headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["charge_id"] == "ch_test_123"
    assert body["client_secret"] == "cs_test_abc"
    assert body["status"] == "pending"


def test_webhook_is_idempotent(client) -> None:
    headers = _auth(client)
    order_id = _place_order(client, headers)
    client.post(f"/api/orders/{order_id}/pay", headers=headers)

    event = {
        "id": "evt_001",
        "type": "charge.succeeded",
        "data": {"charge_id": "ch_test_123"},
    }
    # first delivery → processed; order transitions to paid
    first = _post_webhook(client, event)
    assert first.status_code == 201
    assert first.json()["status"] == "processed"
    assert client.get("/api/orders", headers=headers).json()[0]["status"] == "paid"

    # redelivery of the SAME event id → acknowledged but not reprocessed
    second = _post_webhook(client, event)
    assert second.status_code == 201
    assert second.json()["status"] == "already_processed"
    # still paid (and only one webhook_event recorded — idempotent)
    assert client.get("/api/orders", headers=headers).json()[0]["status"] == "paid"


def test_webhook_malformed_is_400(client) -> None:
    assert _post_webhook(client, {"id": "x"}).status_code == 400


def test_webhook_without_valid_signature_is_rejected(client) -> None:
    """An unsigned or forged webhook can't transition an order — the core anti-fraud check."""
    headers = _auth(client)
    order_id = _place_order(client, headers)
    client.post(f"/api/orders/{order_id}/pay", headers=headers)
    event = {
        "id": "evt_forged",
        "type": "charge.succeeded",
        "data": {"charge_id": "ch_test_123"},
    }

    # no signature → 401
    assert _post_webhook(client, event, sign=False).status_code == 401
    # wrong signature → 401
    body = json.dumps(event).encode()
    forged = client.post(
        "/api/webhooks/payment",
        content=body,
        headers={"Content-Type": "application/json", "X-Signature": "deadbeef"},
    )
    assert forged.status_code == 401
    # the order was NOT marked paid by the forgery attempts
    assert client.get("/api/orders", headers=headers).json()[0]["status"] == "pending"
