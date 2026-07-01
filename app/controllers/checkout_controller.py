"""Checkout + orders — turn a cart into an order atomically, fire a domain event, and drive the
order state machine. Typed end to end (request, response schemas).

Exercises arvel's DB transactions (DB.transaction — order + items created and the cart cleared
atomically; a failure rolls all of it back), events (Event.dispatch('order.placed') → the registered
listener), telemetry (a checkout span), and the typed OrderStatus state machine (app.enums).
"""

from arvel import DB, Cache, Event, abort
from arvel.http import Request
from arvel.support import current_user
from arvel.telemetry import span
from arvel.validation import ValidationException

from app.controllers.cart_controller import resolve_cart
from app.enums import OrderStatus, Permission, can_transition
from app.events.order_placed import OrderPlaced
from app.jobs.fulfill_order import ORDERS_FULFILLED_KEY
from app.listeners.record_order_metrics import ORDERS_PLACED_KEY
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product_variant import ProductVariant
from app.schemas import MetricsOut, OrderLineOut, OrderOut, OrderStatusIn


def _status_value(order: Order) -> str:
    status = order.status
    return status.value if isinstance(status, OrderStatus) else str(status)


def _order_out(order: Order, items: list[OrderItem]) -> OrderOut:
    return OrderOut(
        id=order.id,
        status=_status_value(order),
        total_cents=order.total_cents,
        items=[
            OrderLineOut(
                product_variant_id=i.product_variant_id,
                quantity=i.quantity,
                unit_price_cents=i.unit_price_cents,
            )
            for i in items
        ],
    )


async def checkout(request: Request) -> OrderOut:
    """Convert the current cart into a PENDING order, atomically (stock locked, cart cleared)."""
    cart, _ = await resolve_cart(request, create=False)
    if cart is None:
        abort(422, "Your cart is empty.")
    items = await cart.items().get()
    if not items:
        abort(422, "Your cart is empty.")

    total = sum(i.unit_price_cents * i.quantity for i in items)
    user = current_user.get()

    # a business span over the whole checkout — the DB queries inside auto-nest under it.
    with span(
        "checkout.place_order",
        attributes={"checkout.total_cents": total, "checkout.line_count": len(items)},
    ):
        async with DB.transaction():
            # Decrement stock under SELECT ... FOR UPDATE so concurrent checkouts can't oversell.
            for item in items:
                variant = (
                    await ProductVariant.where("id", item.product_variant_id)
                    .lock_for_update()
                    .first()
                )
                if variant is None:
                    abort(404, "Product variant not found")
                if variant.stock < item.quantity:
                    # rolls the whole transaction back — no stock taken, no order created
                    raise ValidationException(
                        {
                            "product_variant_id": [
                                f"Insufficient stock for {item.product_variant_id}."
                            ]
                        },
                        status=409,
                    )
                variant.stock = variant.stock - item.quantity
                await variant.save()

            order = await Order.create(
                user_id=user.id if user is not None else None,
                status=OrderStatus.PENDING,
                total_cents=total,
            )
            order_items: list[OrderItem] = []
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
        OrderPlaced(
            order_id=order.id, user_id=order.user_id, total_cents=order.total_cents
        ),
    )
    return _order_out(order, order_items)


async def orders_placed_count(request: Request) -> MetricsOut:
    """Order metrics bumped by the order.placed listeners (proves event→listener + the queued job)."""
    return MetricsOut(
        orders_placed=int(await Cache.get(ORDERS_PLACED_KEY, 0)),
        orders_fulfilled=int(await Cache.get(ORDERS_FULFILLED_KEY, 0)),
    )


async def my_orders(request: Request) -> list[OrderOut]:
    """The authenticated user's orders (newest first)."""
    user = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    orders = await Order.where("user_id", user.id).order_by("id", "desc").get()
    return [_order_out(o, await o.items().get()) for o in orders]


async def update_status(request: Request, data: OrderStatusIn) -> OrderOut:
    """Transition an order, enforcing the state machine. Requires orders.update (guests already 401'd)."""
    user = current_user.get()
    if user is None or not await user.can(Permission.ORDERS_UPDATE.value):
        abort(403, "You may not change order status.")
    order = await Order.find_or_fail(int(request.path_param("id")))
    try:
        target = OrderStatus(data.status)
    except ValueError:
        raise ValidationException(
            {"status": [f"Unknown status '{data.status}'."]}
        ) from None
    current = (
        order.status
        if isinstance(order.status, OrderStatus)
        else OrderStatus(order.status)
    )
    if not can_transition(current, target):
        raise ValidationException(
            {"status": [f"Cannot transition from {current.value} to {target.value}."]}
        )
    order.status = target
    await order.save()
    return _order_out(order, await order.items().get())
