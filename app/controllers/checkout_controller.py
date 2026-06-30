"""Checkout + orders — turn a cart into an order atomically, fire a domain event, and drive the
order state machine.

Exercises arvel's DB transactions (DB.transaction — the order + items are created and the cart
cleared atomically; a failure rolls all of it back), events (Event.dispatch('order.placed') →
the registered listener), validation, and the typed OrderStatus state machine (app.enums).
"""

from typing import Any

from arvel import DB, Event, abort
from arvel.support import current_user

from app.controllers.cart_controller import _resolve_cart
from app.enums import OrderStatus, can_transition
from app.events.order_placed import OrderPlaced
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem


def _order_dict(order: Order, items: list[OrderItem]) -> dict[str, Any]:
    return {
        "id": order.id,
        "status": order.status.value if isinstance(order.status, OrderStatus) else order.status,
        "total_cents": order.total_cents,
        "items": [
            {
                "product_variant_id": i.product_variant_id,
                "quantity": i.quantity,
                "unit_price_cents": i.unit_price_cents,
            }
            for i in items
        ],
    }


async def checkout(request) -> Any:
    """POST /api/checkout — convert the current cart into a PENDING order, atomically."""
    cart, _ = await _resolve_cart(request, create=False)
    if cart is None:
        abort(422, "Your cart is empty.")
    items = await cart.items().get()
    if not items:
        abort(422, "Your cart is empty.")

    total = sum(i.unit_price_cents * i.quantity for i in items)
    user = current_user.get()

    # Atomic: the order + its lines are created and the cart is cleared together. If anything
    # raises, the whole unit rolls back — no half-placed order, no half-cleared cart.
    async with DB.transaction():
        order = await Order.create(
            user_id=user.id if user is not None else None,
            status=OrderStatus.PENDING,
            total_cents=total,
        )
        order_items = []
        for item in items:
            order_items.append(
                await OrderItem.create(
                    order_id=order.id,
                    product_variant_id=item.product_variant_id,
                    quantity=item.quantity,
                    unit_price_cents=item.unit_price_cents,
                )
            )
        await CartItem.where("cart_id", cart.id).delete()
        await cart.delete()

    # the listener (record_order_metrics) reacts — the controller doesn't know about it
    await Event.dispatch(
        "order.placed",
        OrderPlaced(order_id=order.id, user_id=order.user_id, total_cents=order.total_cents),
    )
    from arvel.http import Response

    return Response(content=_order_dict(order, order_items), status=201)


async def orders_placed_count(request) -> Any:
    """GET /api/metrics/orders-placed — the placed-orders counter the OrderPlaced listener bumps
    (proves the event → listener path ran, end to end)."""
    from arvel import Cache

    from app.listeners.record_order_metrics import ORDERS_PLACED_KEY

    return {"orders_placed": int(await Cache.get(ORDERS_PLACED_KEY, 0))}


async def my_orders(request) -> Any:
    """GET /api/orders — the authenticated user's orders (newest first)."""
    user = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    orders = await Order.query().where("user_id", user.id).order_by("id", "desc").get()
    return [_order_dict(o, await o.items().get()) for o in orders]


async def update_status(request) -> Any:
    """POST /api/admin/orders/{id}/status — transition an order, enforcing the state machine.
    Admin-only (the Authenticate middleware already rejected guests)."""
    user = current_user.get()
    if user is None or not user.is_admin():
        abort(403, "Only admins may change order status.")
    order = await Order.find(int(request.path_param("id")))
    if order is None:
        abort(404, "Order not found")
    data = await request.json()
    raw = data.get("status", "")
    try:
        target = OrderStatus(raw)
    except ValueError:
        abort(422, {"status": [f"Unknown status '{raw}'."]})
    current = order.status if isinstance(order.status, OrderStatus) else OrderStatus(order.status)
    if not can_transition(current, target):
        abort(422, {"status": [f"Cannot transition from {current.value} to {target.value}."]})
    order.status = target
    await order.save()
    from arvel.http import Response

    # a state transition is a 200 (not a 201) — POST defaults to 201, so set it explicitly
    return Response(content=_order_dict(order, await order.items().get()), status=200)
