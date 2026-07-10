"""Refund service — the reverse of pay(): route a PAID/SHIPPED order's refund through the mock
PSP boundary. One function; both the customer /cancel and the admin /refund entry points share it,
so the money invariant (refund at most once) lives in exactly one place, not two.
"""

from typing import Any
from app.i18n import trans

from arvel import DB, Http, abort
from arvel.support.facades import Config
from arvel.validation import ValidationException

from app.enums import OrderStatus, PaymentStatus, RefundStatus, can_transition
from app.models.order import Order
from app.models.payment import Payment
from app.models.refund import Refund


def _status(order: Order) -> OrderStatus:
    return (
        order.status
        if isinstance(order.status, OrderStatus)
        else OrderStatus(order.status)
    )


async def initiate_refund(order: Order) -> Refund:
    """Refund the order's SUCCEEDED payment in full.

    Transitions PAID/SHIPPED -> REFUND_PENDING under order `FOR UPDATE`, creates the Refund row
    (amount = the payment's, server-derived), and COMMITS — only THEN is the reverse charge POSTed
    to the gateway. A second concurrent call blocks on the row lock, then sees REFUND_PENDING
    (can_transition is False) and 409s BEFORE any reverse call is made: two clicks can never fire
    two reverse charges. `restock` is derived from the LOCKED current state (PAID -> True, SHIPPED
    -> False, i.e. a return doesn't restock — the goods are physically out), not from a caller
    flag, so it can't go stale between a route reading the order and this function locking it.
    """
    async with DB.transaction():
        locked = await Order.where("id", order.id).lock_for_update().first()
        if locked is None:
            abort(404, trans("shop.errors.order_not_found"))
        current = _status(locked)
        if not can_transition(current, OrderStatus.REFUND_PENDING):
            raise ValidationException(
                {
                    "order": [
                        trans("shop.errors.order_not_refundable", status=current.value)
                    ]
                },
                status=409,
            )
        # the latest SUCCEEDED payment is the money to reverse. A COD order (never charged
        # online) has none, so it 422s here with no state change and no gateway call — the same
        # outcome PENDING/CANCELLED/DELIVERED/REFUNDED already got from the can_transition check
        # above; no separate "is this COD" branch is needed, the payment lookup already covers it.
        payment = (
            await Payment.where("order_id", locked.id)
            .where("status", PaymentStatus.SUCCEEDED.value)
            .order_by("id", "desc")
            .first()
        )
        if payment is None:
            raise ValidationException(
                {"order": [trans("shop.errors.nothing_to_refund")]},
                status=422,
            )
        refund = await Refund.create(
            order_id=locked.id,
            payment_id=payment.id,
            gateway_charge_id=payment.gateway_charge_id,
            amount_cents=payment.amount_cents,  # server-derived, integer cents — never client-sent
            status=RefundStatus.PENDING,
            restock=current is OrderStatus.PAID,
        )
        before = current
        locked.status = OrderStatus.REFUND_PENDING
        await locked.save()
        from app.controllers.checkout_controller import log_transition

        await log_transition(locked, before, OrderStatus.REFUND_PENDING)

    # The reverse gateway call happens AFTER the committed transition, deliberately outside the
    # transaction above: the REFUND_PENDING state + the partial-unique index are already the guard
    # by the time any money moves, and no DB row lock is held across this network round-trip.
    # ponytail: no idempotency key on this POST (fine against the mock — it can't lose a 2xx) and
    # a crash right here leaves the order stuck REFUND_PENDING (a liveness gap, not a safety one —
    # guard 1 still holds). Real-PSP hardening, anti-scope for K15 (mock PSP boundary): send an
    # idempotency key derived from refund.id, and add a reconciliation sweep for stuck
    # REFUND_PENDING rows past some age.
    gateway = Config.get("services.payment_gateway.url")
    secret = Config.get("services.payment_gateway.secret")
    response = await Http.with_token(secret).post(
        f"{gateway}/refunds",
        json={
            "charge_id": refund.gateway_charge_id,
            "amount": refund.amount_cents,
            "order_id": locked.id,
        },
    )
    if not response.successful():
        # Synchronous failure path: no webhook is coming for THIS attempt, so revert here rather
        # than leave the order stuck — mark the Refund FAILED and give the order back to PAID so a
        # retry is possible (REFUND_PENDING -> PAID is the one recovery edge in ORDER_TRANSITIONS).
        # This can't race the success webhook: there is nothing in flight to redeliver.
        async with DB.transaction():
            refund.status = RefundStatus.FAILED
            await refund.save()
            retry_locked = await Order.where("id", locked.id).lock_for_update().first()
            if retry_locked is not None:
                retry_current = _status(retry_locked)
                if can_transition(retry_current, OrderStatus.PAID):
                    retry_locked.status = OrderStatus.PAID
                    await retry_locked.save()
                    from app.controllers.checkout_controller import log_transition

                    await log_transition(retry_locked, retry_current, OrderStatus.PAID)
        abort(502, trans("shop.errors.refund_gateway_error"))

    refund_response: dict[str, Any] = response.json()
    refund.gateway_refund_id = refund_response.get("id")
    await refund.save()
    return refund
