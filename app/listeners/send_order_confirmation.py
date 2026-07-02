"""A listener for OrderPlaced — emails the customer their order confirmation. Decoupled from the
checkout controller: it reacts to the event, the controller doesn't know about it."""

from arvel.support.facades import Mail

from app.events.order_placed import OrderPlaced
from app.mail.order_confirmation import OrderConfirmation


async def send_order_confirmation(event: OrderPlaced) -> None:
    await Mail.to(event.contact_email).send(
        OrderConfirmation(event.order_id, event.total_cents)
    )
