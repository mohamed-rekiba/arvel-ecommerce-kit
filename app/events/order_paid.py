"""The OrderPaid broadcast event — fired when an order flips to PAID.

Rides `ShouldBroadcast`'s default after-commit + queued delivery (dispatcher.py), so it only ever
publishes once the PAID row is durably committed — a rolled-back webhook never emits. The SPA's
checkout confirmation subscribes to the order's private channel instead of polling for this.
"""

from __future__ import annotations

from dataclasses import dataclass

from arvel.broadcasting import PrivateChannel
from arvel.events import ShouldBroadcast


@dataclass
class OrderPaid(ShouldBroadcast):
    """Payload for the `order.{id}` private channel's `OrderPaid` event."""

    order_id: int
    paid_at: (
        str | None
    )  # ISO 8601 — the order's updated_at at the moment it flipped PAID

    def broadcast_on(self) -> list[PrivateChannel]:
        return [PrivateChannel(f"order.{self.order_id}")]

    def broadcast_with(self) -> dict[str, object]:
        return {"order_id": self.order_id, "status": "paid", "paid_at": self.paid_at}
