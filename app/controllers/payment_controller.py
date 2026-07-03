"""Payments — create a charge against the payment gateway (HTTP client) and process gateway
webhooks idempotently. Typed end to end.

Exercises arvel's Http client (outbound gateway call), config, the OrderStatus state machine, and
idempotency: a webhook redelivered with the same event id is processed exactly once (a unique
idempotency-ledger row dedupes it).
"""

import hashlib
import hmac
from typing import Any

from arvel import DB, Http, abort
from arvel.http import Request
from arvel.support.facades import Config
from arvel.validation import ValidationException

from app.controllers.order_access import resolve_owned_order

from app.enums import OrderStatus, PaymentStatus, can_transition
from app.models.order import Order
from app.models.payment import Payment
from app.models.webhook_event import WebhookEvent
from app.schemas import PaymentOut, WebhookIn, WebhookOut

SIGNATURE_HEADER = "X-Signature"


async def _verify_signature(request: Request) -> None:
    """Reject the webhook unless it carries a valid gateway HMAC-SHA256 signature over the raw body.
    Without this, anyone could POST a `charge.succeeded` and mark an order PAID for free."""
    secret = Config.get("services.payment_gateway.secret") or ""
    # fail closed outside debug: the shipped "test-secret" default is publicly known, so a deploy
    # that forgot to set PAYMENT_GATEWAY_SECRET must not verify forged webhooks against it
    if secret == "test-secret" and not Config.get("app.debug", False):
        abort(401, "Invalid webhook signature.")
    provided = request.header(SIGNATURE_HEADER, "") or ""
    expected = hmac.new(
        secret.encode(), await request.raw.body(), hashlib.sha256
    ).hexdigest()
    if not secret or not hmac.compare_digest(provided, expected):
        abort(401, "Invalid webhook signature.")


async def pay(request: Request) -> PaymentOut:
    """Create a charge for the order via the gateway — the signed-in owner or the guest holding
    the order's access token (guests must be able to pay; PENDING-only)."""
    order = await resolve_owned_order(request, int(request.path_param("id")))
    method = getattr(order, "payment_method", None) or "gateway"
    if str(method) == "cod" or getattr(method, "value", "") == "cod":
        abort(422, "This order is cash on delivery — nothing to pay online.")
    status = (
        order.status
        if isinstance(order.status, OrderStatus)
        else OrderStatus(order.status)
    )
    if status is not OrderStatus.PENDING:
        raise ValidationException(
            {"order": [f"Order is already {status.value}."]}, status=409
        )

    gateway = Config.get("services.payment_gateway.url")
    secret = Config.get("services.payment_gateway.secret")
    # outbound gateway call via arvel's Http client (faked with a MockTransport in tests)
    response = await Http.with_token(secret).post(
        f"{gateway}/charges",
        json={"amount": order.total_cents, "currency": "usd", "order_id": order.id},
    )
    if response.status_code >= 400:
        abort(502, "Payment gateway error.")
    charge: dict[str, Any] = response.json()

    payment = await Payment.create(
        order_id=order.id,
        gateway_charge_id=charge["id"],
        amount_cents=order.total_cents,
        status=PaymentStatus.PENDING,
    )
    return PaymentOut(
        payment_id=payment.id,
        charge_id=str(charge["id"]),
        client_secret=charge.get("client_secret"),
        status="pending",
    )


async def webhook(request: Request, data: WebhookIn) -> WebhookOut:
    """Idempotently process a gateway webhook — a redelivery of the same event id is a no-op. The
    request must carry a valid gateway signature (authenticity) before any side effects run."""
    await _verify_signature(request)
    if not data.id or not data.type:
        abort(400, "Malformed webhook.")

    # Idempotency: if this event id is already recorded, it's a redelivery — acknowledge without
    # re-running the side effects.
    if await WebhookEvent.where("event_id", data.id).first() is not None:
        return WebhookOut(status="already_processed")

    async with DB.transaction():
        await WebhookEvent.create(event_id=data.id, type=data.type)
        if data.type == "charge.succeeded":
            charge_id = data.data.get("charge_id")
            payment = await Payment.where("gateway_charge_id", charge_id).first()
            if payment is not None:
                payment.status = PaymentStatus.SUCCEEDED
                await payment.save()
                order = await Order.find(payment.order_id)
                if order is not None:
                    current = (
                        order.status
                        if isinstance(order.status, OrderStatus)
                        else OrderStatus(order.status)
                    )
                    if can_transition(current, OrderStatus.PAID):
                        order.status = OrderStatus.PAID
                        await order.save()
        elif data.type == "charge.failed":
            # the charge died at the gateway: mark the payment failed; the order stays PENDING
            # so the customer can retry payment
            charge_id = data.data.get("charge_id")
            payment = await Payment.where("gateway_charge_id", charge_id).first()
            if payment is not None:
                payment.status = PaymentStatus.FAILED
                await payment.save()
    return WebhookOut(status="processed")
