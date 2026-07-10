"""Payments — gateway charge via the Http client (faked with a MockTransport) + idempotent webhook
processing, through the real served path. A redelivered webhook is processed exactly once.
"""

import asyncio
import hashlib
import hmac
import json
import os

import httpx
import pytest
from litestar.testing import TestClient

from arvel.client import Client
from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.shipping_method import ShippingMethod
from app.models.user import User
from tests.checkout_helpers import checkout_body

_WEBHOOK_SECRET = os.environ[
    "PAYMENT_GATEWAY_SECRET"
]  # set in tests/conftest.py (non-default)


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
        # a charge is a resource creation — the gateway answers 201, not 200; the
        # controller must treat any 2xx as success, not exactly-200
        return httpx.Response(
            201, json={"id": "ch_test_123", "client_secret": "cs_test_abc"}
        )
    return httpx.Response(404, json={"error": "not found"})


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'payments.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product, ProductVariant, ShippingMethod):
            model.set_connection(db)
        _verified_customer = await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        await _verified_customer.mark_email_as_verified()
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
        await ShippingMethod.create(
            code="standard", name="Standard", rate_cents=500, active=True, sort=0
        )
        for model in (User, Category, Product, ProductVariant, ShippingMethod):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())

    from bootstrap.app import create_app

    app = create_app()
    asgi = app.as_asgi()  # registers providers first (incl. the default "http" binding)
    # fake the payment gateway by rebinding "http" with a MockTransport (no real network) — AFTER
    # as_asgi, so provider registration doesn't clobber the override.
    app.instance("http", Client(transport=httpx.MockTransport(_gateway_handler)))
    with TestClient(app=asgi) as test_client:
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
    return client.post("/api/checkout", json=checkout_body(), headers=headers).json()[
        "id"
    ]


def _place_guest_order(client) -> dict:
    """A guest cart → checkout; returns the order json (incl. the access token)."""
    cart_token = client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}
    ).json()["cart_token"]
    placed = client.post(
        "/api/checkout",
        json=checkout_body(email="guest@example.com"),
        headers={"X-Cart-Token": cart_token},
    )
    assert placed.status_code == 201, placed.text
    return placed.json()


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


def test_shipped_default_secret_fails_closed_outside_debug(client) -> None:
    """A deploy that never set PAYMENT_GATEWAY_SECRET must not verify webhooks against the
    publicly-known shipped default — even a correctly-signed request is rejected."""
    from arvel.support.facades import Config

    original = Config.get("services.payment_gateway.secret")
    Config.set("services.payment_gateway.secret", "test-secret")
    Config.set("app.debug", False)
    try:
        event = {"id": "evt_default", "type": "charge.succeeded", "data": {}}
        body = json.dumps(event).encode()
        signed = client.post(
            "/api/webhooks/payment",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": hmac.new(
                    b"test-secret", body, hashlib.sha256
                ).hexdigest(),
            },
        )
        assert signed.status_code == 401
        # in debug (local dev with the stub gateway) the default still works
        Config.set("app.debug", True)
        ok = client.post(
            "/api/webhooks/payment",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": hmac.new(
                    b"test-secret", body, hashlib.sha256
                ).hexdigest(),
            },
        )
        assert ok.status_code == 201
    finally:
        Config.set("services.payment_gateway.secret", original)
        Config.set("app.debug", False)


def test_guest_pays_with_the_order_token(client) -> None:
    """S4: possession of the order token (the checkout receipt) authorizes a guest to pay —
    and to read the order; anything else gets the deny model."""
    order = _place_guest_order(client)
    order_id, token = order["id"], order["token"]

    # no credentials at all → 401
    assert client.post(f"/api/orders/{order_id}/pay").status_code == 401
    # a wrong token → 404 (existence not leaked)
    assert (
        client.post(
            f"/api/orders/{order_id}/pay", headers={"X-Order-Token": "not-the-token"}
        ).status_code
        == 404
    )
    # another signed-in customer → 404
    other = _auth(client)
    assert client.post(f"/api/orders/{order_id}/pay", headers=other).status_code == 404
    assert client.get(f"/api/orders/{order_id}", headers=other).status_code == 404

    # the token holder pays
    paid = client.post(f"/api/orders/{order_id}/pay", headers={"X-Order-Token": token})
    assert paid.status_code == 201
    assert paid.json()["charge_id"] == "ch_test_123"

    # and reads the order (payment attempt visible, still pending until the webhook)
    shown = client.get(f"/api/orders/{order_id}", headers={"X-Order-Token": token})
    assert shown.status_code == 200
    assert shown.json()["payment_status"] == "pending"
    assert shown.json()["status"] == "pending"


def test_charge_failed_leaves_the_order_payable(client) -> None:
    """S4 failure path: charge.failed marks the payment failed; the order stays PENDING (retryable)
    and the read model shows the distinction."""
    order = _place_guest_order(client)
    order_id, token = order["id"], order["token"]
    client.post(f"/api/orders/{order_id}/pay", headers={"X-Order-Token": token})

    failed = _post_webhook(
        client,
        {
            "id": "evt_fail_1",
            "type": "charge.failed",
            "data": {"charge_id": "ch_test_123"},
        },
    )
    assert failed.status_code == 201 and failed.json()["status"] == "processed"

    shown = client.get(
        f"/api/orders/{order_id}", headers={"X-Order-Token": token}
    ).json()
    assert shown["status"] == "pending"  # still payable
    assert shown["payment_status"] == "failed"

    # a retry is allowed (PENDING-only guard doesn't block after a failure)
    assert (
        client.post(
            f"/api/orders/{order_id}/pay", headers={"X-Order-Token": token}
        ).status_code
        == 201
    )


def test_paying_a_paid_order_is_409(client) -> None:
    headers = _auth(client)
    order_id = _place_order(client, headers)
    client.post(f"/api/orders/{order_id}/pay", headers=headers)
    _post_webhook(
        client,
        {
            "id": "evt_paid_1",
            "type": "charge.succeeded",
            "data": {"charge_id": "ch_test_123"},
        },
    )
    assert (
        client.post(f"/api/orders/{order_id}/pay", headers=headers).status_code == 409
    )
