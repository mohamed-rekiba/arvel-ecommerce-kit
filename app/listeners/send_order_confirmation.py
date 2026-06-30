"""A listener for OrderPlaced — emails the customer their order confirmation. Decoupled from the
checkout controller: it reacts to the event, the controller doesn't know about it."""

from arvel.support.facades import Mail

from app.events.order_placed import OrderPlaced
from app.mail.order_confirmation import OrderConfirmation
from app.models.user import User


async def send_order_confirmation(event: OrderPlaced) -> None:
    if event.user_id is None:
        return  # guest checkout has no email on file
    user = await User.find(event.user_id)
    if user is None:
        return
    await Mail.to(user.email).send(OrderConfirmation(event.order_id, event.total_cents))
