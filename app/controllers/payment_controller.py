"""Payments — create a charge against the payment gateway (HTTP client) and process gateway
webhooks idempotently.

Exercises arvel's Http client (outbound gateway call), config, the OrderStatus state machine, and
idempotency: a webhook redelivered with the same event id is processed exactly once (a unique
idempotency-ledger row dedupes it).
"""

from typing import Any

from arvel import DB, Http, abort
from arvel.support import current_user
from arvel.support.facades import Config

from app.enums import OrderStatus, PaymentStatus, can_transition
from app.models.order import Order
from app.models.payment import Payment
from app.models.webhook_event import WebhookEvent


async def pay(request) -> Any:
    """POST /api/orders/{id}/pay — create a charge for the order via the gateway."""
    user = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    order = await Order.find(int(request.path_param("id")))
    if order is None or order.user_id != user.id:
        abort(404, "Order not found")
    status = order.status if isinstance(order.status, OrderStatus) else OrderStatus(order.status)
    if status is not OrderStatus.PENDING:
        abort(409, {"message": f"Order is already {status.value}."})

    gateway = Config.get("services.payment_gateway.url")
    secret = Config.get("services.payment_gateway.secret")
    # outbound gateway call via arvel's Http client (faked with a MockTransport in tests)
    response = await Http.with_token(secret).post(
        f"{gateway}/charges",
        json={"amount": order.total_cents, "currency": "usd", "order_id": order.id},
    )
    if response.status_code >= 400:
        abort(502, {"message": "Payment gateway error."})
    charge = response.json()

    payment = await Payment.create(
        order_id=order.id,
        gateway_charge_id=charge["id"],
        amount_cents=order.total_cents,
        status=PaymentStatus.PENDING,
    )
    return {
        "payment_id": payment.id,
        "charge_id": charge["id"],
        "client_secret": charge.get("client_secret"),
        "status": "pending",
    }


async def webhook(request) -> Any:
    """POST /api/webhooks/payment — idempotently process a gateway webhook. A redelivery of the
    same event id is a no-op (already processed → 200)."""
    payload = await request.json()
    event_id = payload.get("id")
    event_type = payload.get("type")
    if not event_id or not event_type:
        abort(400, {"message": "Malformed webhook."})

    # Idempotency: record the event id first (unique). If it's already recorded, this is a
    # redelivery — acknowledge without re-running the side effects.
    if await WebhookEvent.query().where("event_id", event_id).first() is not None:
        return {"status": "already_processed"}

    async with DB.transaction():
        await WebhookEvent.create(event_id=event_id, type=event_type)
        if event_type == "charge.succeeded":
            charge_id = payload.get("data", {}).get("charge_id")
            payment = await Payment.query().where("gateway_charge_id", charge_id).first()
            if payment is not None:
                payment.status = PaymentStatus.SUCCEEDED
                await payment.save()
                order = await Order.find(payment.order_id)
                current = (
                    order.status
                    if isinstance(order.status, OrderStatus)
                    else OrderStatus(order.status)
                )
                if can_transition(current, OrderStatus.PAID):
                    order.status = OrderStatus.PAID
                    await order.save()
    return {"status": "processed"}
