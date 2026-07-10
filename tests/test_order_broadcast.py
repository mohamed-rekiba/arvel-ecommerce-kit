"""K9 — order-paid broadcasting: `OrderPaid` fires on the webhook's PAID transition (the log
driver records it here — the network path is proven at the integration/e2e tier), and the private
`order.{id}` channel's channel-auth denies a non-owner (403) while authorizing the owner — both
through the real served app, exercising arvel's own `/broadcasting/auth` endpoint.
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
from arvel.kernel import Application

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.shipping_method import ShippingMethod
from app.models.user import User
from tests.checkout_helpers import checkout_body

_WEBHOOK_SECRET = os.environ["PAYMENT_GATEWAY_SECRET"]


def _gateway_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/charges":
        return httpx.Response(
            201, json={"id": "ch_broadcast_1", "client_secret": "cs_test"}
        )
    return httpx.Response(404, json={"error": "not found"})


@pytest.fixture
def app_and_client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'order_broadcast.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product, ProductVariant, ShippingMethod):
            model.set_connection(db)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        await User.create(
            name="Bea",
            email="bea@example.com",
            password="secret-bea",
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
        await ShippingMethod.create(
            code="standard", name="Standard", rate_cents=500, active=True, sort=0
        )
        for model in (User, Category, Product, ProductVariant, ShippingMethod):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())

    from bootstrap.app import create_app

    app: Application = create_app()
    asgi = app.as_asgi()
    app.instance("http", Client(transport=httpx.MockTransport(_gateway_handler)))
    with TestClient(app=asgi) as test_client:
        yield app, test_client


def _auth(client, email, password) -> dict:
    token = client.post(
        "/api/login", json={"email": email, "password": password}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _place_and_pay(client, headers) -> int:
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=headers,
    )
    order_id = client.post(
        "/api/checkout", json=checkout_body(), headers=headers
    ).json()["id"]
    client.post(f"/api/orders/{order_id}/pay", headers=headers)
    return order_id


def _post_webhook(client, event: dict) -> httpx.Response:
    body = json.dumps(event).encode()
    signature = hmac.new(_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return client.post(
        "/api/webhooks/payment",
        content=body,
        headers={"Content-Type": "application/json", "X-Signature": signature},
    )


def test_order_paid_broadcasts_on_the_private_order_channel(app_and_client) -> None:
    app, client = app_and_client
    headers = _auth(client, "cara@example.com", "secret-cara")
    order_id = _place_and_pay(client, headers)

    resp = _post_webhook(
        client,
        {
            "id": "evt_broadcast_1",
            "type": "charge.succeeded",
            "data": {"charge_id": "ch_broadcast_1"},
        },
    )
    assert resp.status_code == 201
    # the broadcast rides the queue (the "memory" driver's task is fire-and-forget — see
    # test_checkout.py's own orders-placed re-fetch); one more request gives the event loop the
    # turns it needs to actually finish that task before we inspect its effect.
    client.get("/api/orders", headers=headers)

    sent = app.make(
        "broadcast"
    ).sent  # the "log" driver (tests/conftest.py) records every send
    matches = [s for s in sent if s[0] == "OrderPaid"]
    assert len(matches) == 1, sent
    event_name, channels, event = matches[0]
    assert channels == [f"private-order.{order_id}"]
    assert event.broadcast_with() == {
        "order_id": order_id,
        "status": "paid",
        "paid_at": event.paid_at,
    }
    assert event.paid_at is not None


def test_order_channel_auth_denies_a_non_owner_and_allows_the_owner(
    app_and_client,
) -> None:
    app, client = app_and_client
    cara = _auth(client, "cara@example.com", "secret-cara")
    bea = _auth(client, "bea@example.com", "secret-bea")
    order_id = _place_and_pay(client, cara)

    # Bea (not the order's owner) requesting Cara's order channel → 403, arvel's own callback deny
    denied = client.post(
        "/broadcasting/auth",
        data={"socket_id": "sid-1", "channel_name": f"private-order.{order_id}"},
        headers=bea,
    )
    assert denied.status_code == 403

    # Cara (the owner) requesting her own order channel → 200 with a signed auth string
    allowed = client.post(
        "/broadcasting/auth",
        data={"socket_id": "sid-1", "channel_name": f"private-order.{order_id}"},
        headers=cara,
    )
    assert allowed.status_code == 200, allowed.text
    assert isinstance(allowed.json()["auth"], str) and allowed.json()["auth"]

    # a guest (no credentials at all) never reaches the callback — 401
    assert (
        client.post(
            "/broadcasting/auth",
            data={"socket_id": "sid-1", "channel_name": f"private-order.{order_id}"},
        ).status_code
        == 401
    )
