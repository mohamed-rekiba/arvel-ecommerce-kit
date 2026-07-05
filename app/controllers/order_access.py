"""Order ownership resolution — who may act on an order.

Two proofs of ownership, matching how the order was placed:
- a signed-in customer owns the orders whose ``user_id`` is theirs (bearer token);
- anyone holding the order's access token (returned once at checkout, kept by the guest's
  browser) owns that order — the digital till receipt.

Deny model: no credentials at all → 401; credentials that don't own the order → 404 (never leak
that the id exists)."""

import hmac

from arvel import abort
from arvel.http import Request
from arvel.support import current_user

from app.models.order import Order

ORDER_TOKEN_HEADER = "X-Order-Token"  # nosec B105


async def resolve_owned_order(
    request: Request, order_id: int, *, query_token: str = ""
) -> Order:
    """``query_token`` lets a route opt in to accepting the receipt token as a query param —
    only the invoice does (a print view opened in a browser tab, where headers can't be set)."""
    user = current_user.get()
    provided_token = request.header(ORDER_TOKEN_HEADER, "") or query_token
    if user is None and not provided_token:
        abort(401, "Unauthenticated")
    order = await Order.find(order_id)
    if order is None:
        abort(404, "Order not found")
    if user is not None and order.user_id == user.id:
        return order
    if provided_token and hmac.compare_digest(provided_token, order.token):
        return order
    abort(404, "Order not found")  # authenticated-but-not-owner: don't leak existence
    raise AssertionError("unreachable")  # abort() raises; keeps the return type honest
