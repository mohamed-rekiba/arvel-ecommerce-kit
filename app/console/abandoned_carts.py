"""Scheduled task: sweep abandoned guest carts.

A guest cart (no user) untouched for longer than the threshold is abandoned — delete it and its
items. Authenticated users keep their carts. Returns the number of carts swept.
"""

from arvel import Date

from app.models.cart import Cart
from app.models.cart_item import CartItem

ABANDONED_AFTER_HOURS = 72


async def sweep_abandoned_carts(
    *, older_than_hours: int = ABANDONED_AFTER_HOURS
) -> int:
    cutoff = Date.now().subtract(hours=older_than_hours)
    stale = (
        await Cart.where("user_id", None)  # guest carts only
        .where("updated_at", "<", cutoff)
        .get()
    )
    for cart in stale:
        await CartItem.where("cart_id", cart.id).delete()
        await cart.delete()
    return len(stale)
