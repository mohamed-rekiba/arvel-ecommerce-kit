"""Deliver a (dev-gateway) webhook back to the shop — the gateway→merchant leg, simulated.

Dispatched by the dev gateway stub when a charge is created, the way a real PSP notifies
asynchronously: an HMAC-signed HTTP POST to the same ``/api/webhooks/payment`` endpoint a real
gateway would hit.
"""

import hashlib
import hmac
import json

from arvel import Http
from arvel.queue import Job
from arvel.support.facades import Config


class DeliverGatewayWebhook(Job):
    def __init__(self, event_id: str, event_type: str, charge_id: str) -> None:
        self.event_id = event_id
        self.event_type = event_type
        self.charge_id = charge_id

    async def handle(self) -> None:
        body = json.dumps(
            {
                "id": self.event_id,
                "type": self.event_type,
                "data": {"charge_id": self.charge_id},
            }
        ).encode()
        secret = str(Config.get("services.payment_gateway.secret") or "")
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        app_url = str(Config.get("app.url") or "http://localhost:8000").rstrip("/")
        await Http.with_headers(
            {"X-Signature": signature, "Content-Type": "application/json"}
        ).post(f"{app_url}/api/webhooks/payment", content=body)
