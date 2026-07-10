"""The StockChanged broadcast event — fired on an authoritative stock write.

Public channel (`stock.{variant_id}`) — stock levels are already public on the product page, so
no channel-auth is needed. `broadcast_stock()` is the one dispatch site every stock-write route
calls, so the broadcast never scatters across controllers (DRY).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from arvel.broadcasting import Channel
from arvel.events import ShouldBroadcast

if TYPE_CHECKING:
    from app.models.product_variant import ProductVariant


@dataclass
class StockChanged(ShouldBroadcast):
    """Payload for the `stock.{variant_id}` public channel's `StockChanged` event."""

    variant_id: int
    stock: int

    def broadcast_on(self) -> list[Channel]:
        return [Channel(f"stock.{self.variant_id}")]

    def broadcast_with(self) -> dict[str, object]:
        return {
            "variant_id": self.variant_id,
            "stock": self.stock,
            "in_stock": self.stock > 0,
        }


async def broadcast_stock(variant: ProductVariant) -> None:
    """Fire `StockChanged` for `variant`'s current stock — call this after the authoritative write,
    never dispatch `StockChanged` directly from a controller."""
    from arvel import Event

    await Event.dispatch(StockChanged(variant_id=variant.id, stock=variant.stock))
