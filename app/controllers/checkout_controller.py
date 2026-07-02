"""Checkout + orders — turn a cart into an order atomically, fire a domain event, and drive the
order state machine. Typed end to end (request, response schemas).

Exercises arvel's DB transactions (DB.transaction — order + items created and the cart cleared
atomically; a failure rolls all of it back), events (Event.dispatch('order.placed') → the registered
listener), telemetry (a checkout span), and the typed OrderStatus state machine (app.enums).
"""

from arvel import DB, Cache, Event, abort
from arvel.http import Request
from arvel.support import Str, current_user
from arvel.telemetry import span
from arvel.validation import ValidationException, Validator

from app.controllers.cart_controller import resolve_cart
from app.controllers.order_access import resolve_owned_order
from app.enums import CountryCode, Currency, OrderStatus, Permission, can_transition
from app.events.order_placed import OrderPlaced
from app.jobs.fulfill_order import ORDERS_FULFILLED_KEY
from app.listeners.record_order_metrics import ORDERS_PLACED_KEY
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.notifications.order_shipped_notification import OrderShippedNotification
from app.models.product_variant import ProductVariant
from app.schemas import (
    AddressOut,
    CheckoutIn,
    MetricsOut,
    OrderLineOut,
    OrderOut,
    OrderStatusIn,
)

# The shop's documented money rules — server-authoritative, never trusted from the client:
# flat-rate shipping per order, and a flat sales-tax percentage on the goods subtotal.
SHIPPING_FLAT_CENTS = 500
TAX_RATE_PERCENT = 10


def _shipping_cents(subtotal_cents: int) -> int:
    return SHIPPING_FLAT_CENTS


def _tax_cents(subtotal_cents: int) -> int:
    return subtotal_cents * TAX_RATE_PERCENT // 100


def _status_value(order: Order) -> str:
    status = order.status
    return status.value if isinstance(status, OrderStatus) else str(status)


def _address_out(order: Order) -> AddressOut:
    return AddressOut(
        name=order.ship_name,
        line1=order.ship_line1,
        line2=order.ship_line2 or None,
        city=order.ship_city,
        postal_code=order.ship_postal_code,
        country=order.ship_country,
    )


def _currency_value(order: Order) -> str:
    currency = order.currency
    return currency.value if isinstance(currency, Currency) else str(currency)


async def _latest_payment_status(order: Order) -> str | None:
    from app.enums import PaymentStatus
    from app.models.payment import Payment

    payment = await Payment.where("order_id", order.id).order_by("id", "desc").first()
    if payment is None:
        return None
    status = payment.status
    return status.value if isinstance(status, PaymentStatus) else str(status)


def _order_out(
    order: Order, items: list[OrderItem], payment_status: str | None = None
) -> OrderOut:
    return OrderOut(
        id=order.id,
        status=_status_value(order),
        token=order.token,
        contact_email=order.contact_email,
        address=_address_out(order),
        subtotal_cents=order.subtotal_cents,
        shipping_cents=order.shipping_cents,
        tax_cents=order.tax_cents,
        total_cents=order.total_cents,
        currency=_currency_value(order),
        payment_status=payment_status,
        items=[
            OrderLineOut(
                product_variant_id=i.product_variant_id,
                quantity=i.quantity,
                unit_price_cents=i.unit_price_cents,
            )
            for i in items
        ],
    )


def _validate_checkout(
    data: CheckoutIn, account_email: str | None
) -> tuple[str, dict[str, str | None]]:
    """Validate contact + address; returns (contact_email, address fields). 422 with field-level
    errors on failure — the amounts are computed server-side and never read from the client."""
    address = data.address
    payload = {
        "email": data.email or account_email or "",
        "name": (address.name if address else None) or "",
        "line1": (address.line1 if address else None) or "",
        "city": (address.city if address else None) or "",
        "postal_code": (address.postal_code if address else None) or "",
        "country": (address.country if address else None) or "",
    }
    validator = Validator(
        payload,
        {
            "email": "required|email",
            "name": "required|string",
            "line1": "required|string",
            "city": "required|string",
            "postal_code": "required|string",
            "country": "required|string",
        },
    )
    errors = dict(validator.errors()) if validator.fails() else {}
    if payload["country"] and payload["country"] not in {c.value for c in CountryCode}:
        errors["country"] = [f"We don't ship to '{payload['country']}'."]
    if errors:
        raise ValidationException(errors)
    fields = {
        "ship_name": payload["name"],
        "ship_line1": payload["line1"],
        "ship_line2": (address.line2 if address else None) or None,
        "ship_city": payload["city"],
        "ship_postal_code": payload["postal_code"],
        "ship_country": payload["country"],
    }
    return payload["email"], fields


async def checkout(request: Request, data: CheckoutIn) -> OrderOut:
    """Convert the current cart into a PENDING order, atomically (stock locked, cart cleared),
    capturing the contact email + shipping address and the server-computed money breakdown."""
    cart, _ = await resolve_cart(request, create=False)
    if cart is None:
        abort(422, "Your cart is empty.")
    items = await cart.items().get()
    if not items:
        abort(422, "Your cart is empty.")

    user = current_user.get()
    contact_email, ship_fields = _validate_checkout(
        data, user.email if user is not None else None
    )
    subtotal = sum(i.unit_price_cents * i.quantity for i in items)
    shipping = _shipping_cents(subtotal)
    tax = _tax_cents(subtotal)
    total = subtotal + shipping + tax

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
                token=Str.random(40),
                contact_email=contact_email,
                subtotal_cents=subtotal,
                shipping_cents=shipping,
                tax_cents=tax,
                total_cents=total,
                currency=Currency.USD,
                **ship_fields,
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
            order_id=order.id,
            user_id=order.user_id,
            total_cents=order.total_cents,
            contact_email=order.contact_email,
        ),
    )
    return _order_out(order, order_items)


async def show(request: Request) -> OrderOut:
    """One order, with lines + breakdown — for the signed-in owner or the order-token holder."""
    order = await resolve_owned_order(request, int(request.path_param("id")))
    return _order_out(
        order,
        await order.items().get(),
        payment_status=await _latest_payment_status(order),
    )


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


async def admin_orders_index(request: Request) -> list[OrderOut]:
    """List every order (newest first) for the back office. Requires orders.view."""
    user = current_user.get()
    if user is None or not await user.can(Permission.ORDERS_VIEW.value):
        abort(403, "You may not view orders.")
    orders = await Order.order_by("id", "desc").get()
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
    # Notify the customer when their order ships — QUEUED (database + mail channels), so the
    # committed transition never waits on (or 500s from) SMTP.
    if target is OrderStatus.SHIPPED and order.user_id is not None:
        customer = await User.find(order.user_id)
        if customer is not None:
            await customer.notify(OrderShippedNotification(order.id))
    return _order_out(order, await order.items().get())
