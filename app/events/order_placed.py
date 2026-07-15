"""The OrderPlaced domain event — dispatched when a checkout completes."""

from dataclasses import dataclass


@dataclass
class OrderPlaced:
    """The order-placed payload. Dispatched as a class event; listeners in app/listeners/ that
    type-hint ``handle(self, event: OrderPlaced)`` are auto-discovered and bound to it."""

    order_id: int
    user_id: int | None
    total_cents: int
    contact_email: str  # captured at checkout — guests get their confirmation too
    currency: str = (
        "USD"  # the order's currency — Money.format needs it, not a hardcoded $
    )
    locale: str = "en"  # the buyer's request locale — mail renders in their language
