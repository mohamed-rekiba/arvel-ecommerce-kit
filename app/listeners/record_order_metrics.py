"""A listener for OrderPlaced — bumps a placed-orders counter in the cache (a stand-in for a real
metrics/notification reaction; demonstrates event → listener decoupling)."""

from arvel import Cache

from app.events.order_placed import OrderPlaced

ORDERS_PLACED_KEY = "metrics:orders_placed"


async def record_order_metrics(event: OrderPlaced) -> None:
    await Cache.increment(ORDERS_PLACED_KEY)
