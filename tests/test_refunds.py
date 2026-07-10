"""K15 — refunds/returns through the real served path: pay -> cancel(PAID) -> REFUND_PENDING ->
charge.refunded -> REFUNDED, mirroring test_payments.py's pay -> charge.succeeded -> PAID. Proves
the three money-invariant guards (state transition under FOR UPDATE + partial-unique, the event_id
ledger, the terminal-state gate) at the sequential/API level; the concurrent-race slice of guard 1
is proven on real Postgres in tests/integration/test_refund_race.py.
"""

import asyncio
import hashlib
import hmac
import json
import os
from types import SimpleNamespace

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
from tests.rbac_helpers import seed_rbac

_WEBHOOK_SECRET = os.environ["PAYMENT_GATEWAY_SECRET"]


def _post_webhook(client, event: dict, *, sign: bool = True):
    body = json.dumps(event).encode()
    headers = {"Content-Type": "application/json"}
    if sign:
        headers["X-Signature"] = hmac.new(
            _WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
    return client.post("/api/webhooks/payment", content=body, headers=headers)


@pytest.fixture
def gw(tmp_path, monkeypatch):
    """A served kit + a mock dev-gateway that answers /charges and /refunds, recording every
    /refunds call it receives (``gw.refund_calls``) and able to fail them on demand
    (``gw.state["fail_refunds"] = True``) — the reverse-call-failure recovery path."""
    url = f"sqlite+aiosqlite:///{tmp_path / 'refunds.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        for model in (User, Category, Product, ProductVariant, ShippingMethod):
            model.set_connection(db)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        admin = await User.create(
            name="Admin",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("super-admin")
        support = await User.create(
            name="Sam",
            email="sam@example.com",
            password="secret-sam",
            role=UserRole.ADMIN,
        )
        await support.assign_role("support")  # orders.view, NOT orders.update
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        p = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee"}},
            slug="tee",
            price_cents=2000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
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
    asgi = app.as_asgi()

    refund_calls: list[dict] = []
    state = {"fail_refunds": False}

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/charges":
            return httpx.Response(
                201, json={"id": "ch_test_123", "client_secret": "cs_test_abc"}
            )
        if request.url.path == "/refunds":
            refund_calls.append(json.loads(request.content))
            if state["fail_refunds"]:
                return httpx.Response(500, json={"error": "gateway down"})
            return httpx.Response(201, json={"id": f"re_test_{len(refund_calls)}"})
        return httpx.Response(404, json={"error": "not found"})

    app.instance("http", Client(transport=httpx.MockTransport(_handler)))
    with TestClient(app=asgi) as test_client:
        yield SimpleNamespace(
            client=test_client, refund_calls=refund_calls, state=state
        )


def _login(client, email, password) -> dict:
    token = client.post(
        "/api/login", json={"email": email, "password": password}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _place_and_pay(gw, *, quantity: int = 2) -> tuple[int, dict, dict]:
    """Cara checks out and pays; the charge.succeeded webhook lands -> PAID. Returns (order_id,
    cara's auth headers, the PAID order body) — ``paid["total_cents"]`` is what Payment.
    amount_cents (and so the refund amount) must equal; computed server-side (shipping + tax), so
    tests read it back rather than hardcode it."""
    cara = _login(gw.client, "cara@example.com", "secret-cara")
    gw.client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": quantity},
        headers=cara,
    )
    order_id = gw.client.post(
        "/api/checkout", json=checkout_body(), headers=cara
    ).json()["id"]
    gw.client.post(f"/api/orders/{order_id}/pay", headers=cara)
    resp = _post_webhook(
        gw.client,
        {
            "id": f"evt_charge_{order_id}",
            "type": "charge.succeeded",
            "data": {"charge_id": "ch_test_123"},
        },
    )
    assert resp.json()["status"] == "processed"
    paid = gw.client.get(f"/api/orders/{order_id}", headers=cara).json()
    assert paid["status"] == "paid"
    return order_id, cara, paid


def _stock(gw) -> int:
    return gw.client.get("/api/products/tee").json()["variants"][0]["stock"]


def test_paid_cancel_refunds_and_restocks_exactly_once(gw) -> None:
    """S5/K15: a paid cancel -> REFUND_PENDING + one reverse call; charge.refunded -> REFUNDED,
    a SUCCEEDED Refund row (amount == the original Payment), and stock restored exactly once."""
    order_id, cara, paid = _place_and_pay(gw, quantity=3)
    assert _stock(gw) == 97  # 100 - 3

    cancelled = gw.client.post(f"/api/orders/{order_id}/cancel", headers=cara)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "refund_pending"
    assert len(gw.refund_calls) == 1  # exactly one reverse call — before any webhook
    assert (
        gw.refund_calls[0]["amount"] == paid["total_cents"]
    )  # server-derived, not client-sent

    refunded = _post_webhook(
        gw.client,
        {
            "id": "evt_refund_1",
            "type": "charge.refunded",
            "data": {"charge_id": "ch_test_123"},
        },
    )
    assert refunded.json()["status"] == "processed"

    shown = gw.client.get(f"/api/orders/{order_id}", headers=cara).json()
    assert shown["status"] == "refunded"
    assert shown["refund"]["status"] == "succeeded"
    assert shown["refund"]["amount_cents"] == paid["total_cents"]
    assert _stock(gw) == 100  # 97 + 3 — restored exactly once


def test_webhook_idempotent_no_double_restock(gw) -> None:
    """A redelivered charge.refunded (same event_id) -> already_processed; no second transition,
    no second restock (guard 2, DR-0058)."""
    order_id, cara, _paid = _place_and_pay(gw, quantity=2)
    gw.client.post(f"/api/orders/{order_id}/cancel", headers=cara)
    event = {
        "id": "evt_refund_dup",
        "type": "charge.refunded",
        "data": {"charge_id": "ch_test_123"},
    }
    first = _post_webhook(gw.client, event)
    assert first.json()["status"] == "processed"
    assert _stock(gw) == 100

    second = _post_webhook(gw.client, event)
    assert second.json()["status"] == "already_processed"
    assert _stock(gw) == 100  # unchanged — not 102
    assert (
        gw.client.get(f"/api/orders/{order_id}", headers=cara).json()["status"]
        == "refunded"
    )


def test_double_refund_rejected_one_reverse_call(gw) -> None:
    """A second cancel on a REFUND_PENDING order -> 409/422, no second reverse call; a third
    attempt after REFUNDED is rejected too (guard 1 + guard 3)."""
    order_id, cara, _paid = _place_and_pay(gw)
    first = gw.client.post(f"/api/orders/{order_id}/cancel", headers=cara)
    assert first.status_code == 200
    assert len(gw.refund_calls) == 1

    again = gw.client.post(f"/api/orders/{order_id}/cancel", headers=cara)
    assert again.status_code in (409, 422)
    assert len(gw.refund_calls) == 1  # no second reverse call issued

    _post_webhook(
        gw.client,
        {
            "id": "evt_r2",
            "type": "charge.refunded",
            "data": {"charge_id": "ch_test_123"},
        },
    )
    assert (
        gw.client.get(f"/api/orders/{order_id}", headers=cara).json()["status"]
        == "refunded"
    )

    after_terminal = gw.client.post(f"/api/orders/{order_id}/cancel", headers=cara)
    assert after_terminal.status_code in (409, 422)
    assert len(gw.refund_calls) == 1


def test_unpaid_and_shipped_cod_refund_rejected(gw) -> None:
    """A PENDING (unpaid) cancel stays the plain synchronous CANCELLED path (no gateway call, no
    Refund row); a COD order that shipped (never online-charged) 422s on refund attempt — no
    successful Payment to reverse."""
    cara = _login(gw.client, "cara@example.com", "secret-cara")
    gw.client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}, headers=cara
    )
    pending_id = gw.client.post(
        "/api/checkout", json=checkout_body(), headers=cara
    ).json()["id"]
    cancelled = gw.client.post(f"/api/orders/{pending_id}/cancel", headers=cara)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert len(gw.refund_calls) == 0  # never touched the gateway

    gw.client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}, headers=cara
    )
    cod_id = gw.client.post(
        "/api/checkout",
        json=checkout_body(payment_method="cod"),
        headers=cara,
    ).json()["id"]
    admin = _login(gw.client, "admin@example.com", "secret-admin")
    ship = gw.client.post(
        f"/api/admin/orders/{cod_id}/status",
        json={"status": "shipped", "tracking_number": "1Z1"},
        headers=admin,
    )
    assert ship.status_code == 200

    refund_attempt = gw.client.post(f"/api/admin/orders/{cod_id}/refund", headers=admin)
    assert refund_attempt.status_code == 422
    assert "Nothing to refund" in refund_attempt.json()["errors"]["order"][0]
    assert len(gw.refund_calls) == 0


def test_admin_shipped_return_refunds_without_restocking(gw) -> None:
    """The one documented return case: an admin refunds a SHIPPED order -> REFUND_PENDING ->
    REFUNDED with restock=False — stock stays at its post-checkout (shipped-out) level."""
    order_id, _cara, _paid = _place_and_pay(gw, quantity=4)
    assert _stock(gw) == 96
    admin = _login(gw.client, "admin@example.com", "secret-admin")
    ship = gw.client.post(
        f"/api/admin/orders/{order_id}/status",
        json={"status": "shipped", "tracking_number": "1Z2"},
        headers=admin,
    )
    assert ship.status_code == 200

    refund = gw.client.post(f"/api/admin/orders/{order_id}/refund", headers=admin)
    assert refund.status_code == 200, refund.text
    assert refund.json()["status"] == "refund_pending"
    assert len(gw.refund_calls) == 1

    _post_webhook(
        gw.client,
        {
            "id": "evt_ship_refund",
            "type": "charge.refunded",
            "data": {"charge_id": "ch_test_123"},
        },
    )
    detail = gw.client.get(f"/api/admin/orders/{order_id}", headers=admin).json()
    assert detail["status"] == "refunded"
    assert detail["refunds"][-1]["restock"] is False
    assert _stock(gw) == 96  # unchanged — goods are physically out, not restocked


def test_generic_status_route_cannot_reach_refund_states(gw) -> None:
    """The generic admin status-transition route can neither move an order INTO REFUND_PENDING/
    REFUNDED (target-direction) NOR OUT of REFUND_PENDING to anything, including "paid" (source-
    direction — the orphaned-refund hole: REFUND_PENDING -> PAID is a real ORDER_TRANSITIONS edge,
    reserved for refund_service's own reverse-call-failure recovery; it must NOT be reachable by
    an admin bare status-flip, or a reverse charge already issued gets stranded PENDING while the
    order reads "paid" and fulfillable)."""
    order_id, cara, _paid = _place_and_pay(gw)
    admin = _login(gw.client, "admin@example.com", "secret-admin")

    # target-direction: can't flip INTO a refund state
    into = gw.client.post(
        f"/api/admin/orders/{order_id}/status",
        json={"status": "refund_pending"},
        headers=admin,
    )
    assert into.status_code == 422
    assert len(gw.refund_calls) == 0

    # source-direction: once genuinely REFUND_PENDING (a real reverse charge in flight), the
    # generic route can't flip it OUT — not even to "paid", which IS a legal ORDER_TRANSITIONS
    # edge, just not through this route.
    cancelled = gw.client.post(f"/api/orders/{order_id}/cancel", headers=cara)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "refund_pending"

    out_to_paid = gw.client.post(
        f"/api/admin/orders/{order_id}/status",
        json={"status": "paid"},
        headers=admin,
    )
    assert out_to_paid.status_code == 422
    assert (
        gw.client.get(f"/api/orders/{order_id}", headers=cara).json()["status"]
        == "refund_pending"
    )  # not orphaned into "paid" — the Refund row is still the only way out

    out_to_shipped = gw.client.post(
        f"/api/admin/orders/{order_id}/status",
        json={"status": "shipped", "tracking_number": "1Z9"},
        headers=admin,
    )
    assert out_to_shipped.status_code == 422


def test_reverse_call_failure_reverts_to_paid_and_retry_succeeds(gw) -> None:
    """A synchronous reverse-call failure marks the Refund FAILED and reverts REFUND_PENDING ->
    PAID (502, retryable) — and the partial-unique index does NOT block the retry once the prior
    attempt is FAILED, not PENDING/SUCCEEDED."""
    order_id, cara, _paid = _place_and_pay(gw)
    gw.state["fail_refunds"] = True
    failed = gw.client.post(f"/api/orders/{order_id}/cancel", headers=cara)
    assert failed.status_code == 502
    assert (
        gw.client.get(f"/api/orders/{order_id}", headers=cara).json()["status"]
        == "paid"
    )
    assert len(gw.refund_calls) == 1

    gw.state["fail_refunds"] = False
    retried = gw.client.post(f"/api/orders/{order_id}/cancel", headers=cara)
    assert retried.status_code == 200
    assert retried.json()["status"] == "refund_pending"
    assert len(gw.refund_calls) == 2


def test_refund_webhook_forged_signature_rejected(gw) -> None:
    """charge.refunded is covered by the SAME type-agnostic signature check as charge.succeeded —
    a forged/unsigned event -> 401, no transition, no restock."""
    order_id, cara, _paid = _place_and_pay(gw, quantity=1)
    gw.client.post(f"/api/orders/{order_id}/cancel", headers=cara)
    stock_before = _stock(gw)

    event = {
        "id": "evt_forged_refund",
        "type": "charge.refunded",
        "data": {"charge_id": "ch_test_123"},
    }
    assert _post_webhook(gw.client, event, sign=False).status_code == 401
    body = json.dumps(event).encode()
    forged = gw.client.post(
        "/api/webhooks/payment",
        content=body,
        headers={"Content-Type": "application/json", "X-Signature": "deadbeef"},
    )
    assert forged.status_code == 401
    assert (
        gw.client.get(f"/api/orders/{order_id}", headers=cara).json()["status"]
        == "refund_pending"
    )
    assert _stock(gw) == stock_before


def test_refund_authz_owner_and_permission_scoped(gw) -> None:
    """A non-owner (no credentials at all) can't cancel/refund someone else's order (401); the
    admin refund route denies a caller lacking orders.update (403) — the deny model, mechanically
    enforced, not just documented."""
    order_id, _cara, _paid = _place_and_pay(gw)
    assert gw.client.post(f"/api/orders/{order_id}/cancel").status_code == 401

    support = _login(
        gw.client, "sam@example.com", "secret-sam"
    )  # orders.view, not .update
    assert (
        gw.client.post(
            f"/api/admin/orders/{order_id}/refund", headers=support
        ).status_code
        == 403
    )
    assert len(gw.refund_calls) == 0


def test_refunded_order_invoice_renders_not_500(gw) -> None:
    """A refunded order's invoice must render (showing the refunded status), not KeyError -> 500 —
    the status-label lookup was missing the refund states."""
    order_id, cara, _paid = _place_and_pay(gw, quantity=1)
    gw.client.post(f"/api/orders/{order_id}/cancel", headers=cara)
    _post_webhook(
        gw.client,
        {
            "id": "evt_refund_inv",
            "type": "charge.refunded",
            "data": {"charge_id": "ch_test_123"},
        },
    )

    page = gw.client.get(f"/api/orders/{order_id}/invoice", headers=cara)
    assert page.status_code == 200, page.text
    assert "refunded" in page.text.lower()


def test_refund_timeline_collapses_to_a_terminal_branch(gw) -> None:
    """The tracking stepper must not imply a refund is still heading to delivery: a refund collapses
    the path to placed -> paid -> refund_pending, then -> refunded — never the greyed
    shipped/delivered steps that showed a delivery tracker on a refunded order."""
    order_id, cara, _paid = _place_and_pay(gw, quantity=1)

    gw.client.post(f"/api/orders/{order_id}/cancel", headers=cara)
    timeline = gw.client.get(f"/api/orders/{order_id}", headers=cara).json()["timeline"]
    assert [s["status"] for s in timeline] == ["pending", "paid", "refund_pending"]
    assert all(
        s["at"] is not None for s in timeline
    )  # a terminal branch has no unreached steps

    _post_webhook(
        gw.client,
        {
            "id": "evt_refund_tl",
            "type": "charge.refunded",
            "data": {"charge_id": "ch_test_123"},
        },
    )
    timeline = gw.client.get(f"/api/orders/{order_id}", headers=cara).json()["timeline"]
    assert [s["status"] for s in timeline] == ["pending", "paid", "refunded"]
    assert all(s["at"] is not None for s in timeline)
