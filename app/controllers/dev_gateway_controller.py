"""A dev-only payment-gateway stub (registered only when app.debug).

Plays the PSP's role so the payment loop runs end-to-end on a real socket with no external
account: the shop's ``pay`` calls POST /api/dev-gateway/charges over real HTTP; the stub "creates"
the charge and — like a real gateway — notifies asynchronously by dispatching a queued
DeliverGatewayWebhook that POSTs the HMAC-signed ``charge.succeeded`` back to the shop's webhook.
"""

from uuid import uuid4

from arvel.http import Request

from app.jobs.deliver_gateway_webhook import DeliverGatewayWebhook
from app.schemas import DevChargeIn, DevChargeOut, DevRefundIn, DevRefundOut


async def create_charge(request: Request, data: DevChargeIn) -> DevChargeOut:
    """Accept a charge and queue the async success webhook (the PSP's notify leg)."""
    charge_id = f"ch_dev_{uuid4().hex[:12]}"
    await DeliverGatewayWebhook.dispatch(
        f"evt_{uuid4().hex[:12]}", "charge.succeeded", charge_id
    )
    return DevChargeOut(id=charge_id, client_secret=f"cs_dev_{uuid4().hex[:8]}")


async def create_refund(request: Request, data: DevRefundIn) -> DevRefundOut:
    """Accept a reverse charge and queue the async ``charge.refunded`` webhook — the direct mirror
    of ``create_charge`` (K15)."""
    refund_id = f"re_dev_{uuid4().hex[:12]}"
    await DeliverGatewayWebhook.dispatch(
        f"evt_{uuid4().hex[:12]}", "charge.refunded", data.charge_id
    )
    return DevRefundOut(id=refund_id)
