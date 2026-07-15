"""Emails the customer their order confirmation when an order is placed. Decoupled from the
checkout controller: it reacts to the event, the controller doesn't know about it.

Auto-discovered from app/listeners/ — bound to OrderPlaced by the handle type hint.
"""

from arvel.support.facades import Mail

from app.events.order_placed import OrderPlaced
from app.mail.order_confirmation import OrderConfirmation


class SendOrderConfirmation:
    async def handle(self, event: OrderPlaced) -> None:
        await Mail.to(event.contact_email).send(
            OrderConfirmation(
                event.order_id,
                event.total_cents,
                currency=event.currency,
                locale=event.locale,
            )
        )
