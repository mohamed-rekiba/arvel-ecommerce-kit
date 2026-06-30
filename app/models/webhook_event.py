"""The WebhookEvent model — the idempotency ledger for inbound gateway webhooks.

Each gateway event id is recorded exactly once (unique). A redelivered webhook collides on the
unique key, so processing is naturally idempotent — the side effects happen at most once.
"""

from typing import ClassVar

from arvel import Model


class WebhookEvent(Model):
    __table_name__ = "webhook_events"
    __fields__: ClassVar[dict[str, type]] = {
        "event_id": str,
        "type": str,
    }
    __fillable__: ClassVar[list[str]] = ["event_id", "type"]
