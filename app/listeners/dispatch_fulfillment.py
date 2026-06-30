"""A listener for OrderPlaced — queues the fulfilment job (background processing)."""

from app.events.order_placed import OrderPlaced
from app.jobs.fulfill_order import FulfillOrderJob


async def dispatch_fulfillment(event: OrderPlaced) -> None:
    await FulfillOrderJob.dispatch(event.order_id)
