"""The OrderPlaced domain event — dispatched when a checkout completes."""

from dataclasses import dataclass


@dataclass
class OrderPlaced:
    """Payload for the ``order.placed`` event."""

    order_id: int
    user_id: int | None
    total_cents: int
    contact_email: str  # captured at checkout — guests get their confirmation too
    locale: str = "en"  # the buyer's request locale — mail renders in their language
