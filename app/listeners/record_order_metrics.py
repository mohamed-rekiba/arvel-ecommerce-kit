"""Bumps a placed-orders counter in the cache when an order is placed (a stand-in for a real
metrics/notification reaction; demonstrates event → listener decoupling).

Auto-discovered from app/listeners/ — bound to OrderPlaced by the handle type hint.
"""

from arvel import Cache

from app.events.order_placed import OrderPlaced

ORDERS_PLACED_KEY = "metrics:orders_placed"


class RecordOrderMetrics:
    async def handle(self, event: OrderPlaced) -> None:
        await Cache.increment(ORDERS_PLACED_KEY)
