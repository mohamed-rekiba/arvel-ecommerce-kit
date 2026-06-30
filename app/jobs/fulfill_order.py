"""A queued job: fulfil a placed order (pick/pack/ship hand-off). Here it bumps a fulfilment
counter as a stand-in for real warehouse work — enough to prove the job ran on the queue."""

from typing import Any

from arvel import Cache
from arvel.queue import Job

ORDERS_FULFILLED_KEY = "metrics:orders_fulfilled"


class FulfillOrderJob(Job):
    def __init__(self, order_id: int) -> None:
        self.order_id = order_id

    async def handle(self) -> Any:
        await Cache.increment(ORDERS_FULFILLED_KEY)
