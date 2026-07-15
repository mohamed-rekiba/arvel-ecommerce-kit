"""Queues the fulfilment job when an order is placed (background processing).

Auto-discovered from app/listeners/ — bound to OrderPlaced by the handle type hint.
"""

from app.events.order_placed import OrderPlaced
from app.jobs.fulfill_order import FulfillOrderJob


class DispatchFulfillment:
    async def handle(self, event: OrderPlaced) -> None:
        await FulfillOrderJob.dispatch(event.order_id)
