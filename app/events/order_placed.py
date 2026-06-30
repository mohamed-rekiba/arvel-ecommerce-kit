"""The OrderPlaced domain event — dispatched when a checkout completes."""

from dataclasses import dataclass


@dataclass
class OrderPlaced:
    """Payload for the ``order.placed`` event."""

    order_id: int
    user_id: int | None
    total_cents: int
