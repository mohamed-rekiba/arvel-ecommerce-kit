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
from app.enums import (
    CountryCode,
    Currency,
    OrderStatus,
    PaymentStatus,
    Permission,
    can_transition,
)
from app.events.order_placed import OrderPlaced
from app.jobs.fulfill_order import ORDERS_FULFILLED_KEY
from app.listeners.record_order_metrics import ORDERS_PLACED_KEY
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.notifications.order_shipped_notification import OrderShippedNotification
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.schemas import (
    AddressOut,
    AdminOrderDetailOut,
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


def _status_value(order: Order) -> OrderStatus:
    status = order.status
    return status if isinstance(status, OrderStatus) else OrderStatus(status)


def _address_out(order: Order) -> AddressOut:
    return AddressOut(
        name=order.ship_name,
        line1=order.ship_line1,
        line2=order.ship_line2 or None,
        city=order.ship_city,
        postal_code=order.ship_postal_code,
        country=CountryCode(order.ship_country),
    )


def _currency_value(order: Order) -> Currency:
    currency = order.currency
    return currency if isinstance(currency, Currency) else Currency(currency)


async def _latest_payment_status(order: Order) -> PaymentStatus | None:
    from app.enums import PaymentStatus
    from app.models.payment import Payment

    payment = await Payment.where("order_id", order.id).order_by("id", "desc").first()
    if payment is None:
        return None
    status = payment.status
    return status if isinstance(status, PaymentStatus) else PaymentStatus(status)


def _order_out(
    order: Order, items: list[OrderItem], payment_status: PaymentStatus | None = None
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
                product_name=i.product_name,
                variant_name=i.variant_name,
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
                if await Product.find(variant.product_id) is None:
                    # the product was archived while sitting in the cart — the line is dead
                    raise ValidationException(
                        {
                            "product_variant_id": [
                                "An item in your cart is no longer available."
                            ]
                        },
                        status=409,
                    )
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
                # purchase-time snapshot of what was bought, as the customer saw it
                variant = await ProductVariant.find_or_fail(item.product_variant_id)
                product = (
                    await Product.in_locale().where("id", variant.product_id).first()
                )
                if product is None:  # a variant always belongs to a product
                    abort(404, "Product not found")
                order_items.append(
                    await OrderItem.create(
                        order_id=order.id,
                        product_variant_id=item.product_variant_id,
                        product_name=product.translation.name,
                        variant_name=variant.name,
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


async def cancel(request: Request) -> OrderOut:
    """Cancel the order (owner or token holder) while the state machine allows it — restoring the
    decremented stock atomically. Cancelling a PAID order records the cancellation; refunding the
    money is out of scope (documented limitation)."""
    order = await resolve_owned_order(request, int(request.path_param("id")))
    async with DB.transaction():
        # re-read under FOR UPDATE: two concurrent cancels serialize here, so exactly one
        # transitions and restocks — the loser sees CANCELLED and 422s
        locked = await Order.where("id", order.id).lock_for_update().first()
        if locked is None:
            abort(404, "Order not found")
        current = (
            locked.status
            if isinstance(locked.status, OrderStatus)
            else OrderStatus(locked.status)
        )
        if not can_transition(current, OrderStatus.CANCELLED):
            raise ValidationException(
                {"order": [f"A {current.value} order can no longer be cancelled."]},
                status=422,
            )
        items = await locked.items().get()
        for item in items:
            variant = (
                await ProductVariant.where("id", item.product_variant_id)
                .lock_for_update()
                .first()
            )
            if variant is not None:
                variant.stock = variant.stock + item.quantity
                await variant.save()
        locked.status = OrderStatus.CANCELLED
        await locked.save()
    return _order_out(
        locked, items, payment_status=await _latest_payment_status(locked)
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


async def admin_order_show(request: Request) -> AdminOrderDetailOut:
    """Everything a staff member needs on one order: lines (purchase snapshots), breakdown,
    address + contact, the customer link (or guest label), payment + webhook-backed states, and
    the transition history from the activity trail. Requires orders.view."""
    from arvel.activitylog import Activity

    from app.enums import PaymentStatus as _PS
    from app.models.payment import Payment
    from app.schemas import (
        AdminOrderCustomerOut,
        AdminOrderDetailOut,
        AdminOrderEventOut,
        AdminOrderPaymentOut,
    )

    user = current_user.get()
    if user is None or not await user.can(Permission.ORDERS_VIEW.value):
        abort(403, "You may not view orders.")
    order = await Order.find_or_fail(int(request.path_param("id")))
    items = await order.items().get()

    customer = None
    if order.user_id is not None:
        owner = await User.find(order.user_id)
        if owner is not None:
            customer = AdminOrderCustomerOut(
                id=owner.id, name=owner.name, email=owner.email
            )

    payments = await Payment.where("order_id", order.id).order_by("id").get()
    events = (
        await Activity.where("subject_type", "Order")
        .where("subject_id", order.id)
        .order_by("id")
        .get()
    )

    def _iso(value: object) -> str | None:
        return None if value is None else str(value)

    return AdminOrderDetailOut(
        id=order.id,
        status=_status_value(order),
        contact_email=order.contact_email,
        address=_address_out(order),
        subtotal_cents=order.subtotal_cents,
        shipping_cents=order.shipping_cents,
        tax_cents=order.tax_cents,
        total_cents=order.total_cents,
        currency=_currency_value(order),
        customer=customer,
        items=[
            OrderLineOut(
                product_variant_id=i.product_variant_id,
                product_name=i.product_name,
                variant_name=i.variant_name,
                quantity=i.quantity,
                unit_price_cents=i.unit_price_cents,
            )
            for i in items
        ],
        payments=[
            AdminOrderPaymentOut(
                id=p.id,
                charge_id=p.gateway_charge_id,
                amount_cents=p.amount_cents,
                status=p.status if isinstance(p.status, _PS) else _PS(p.status),
                created_at=_iso(p.created_at),
            )
            for p in payments
        ],
        history=[
            AdminOrderEventOut(
                description=e.description,
                causer_id=e.causer_id,
                properties={
                    str(k): str(v)
                    for k, v in dict(e.properties or {}).items()  # type: ignore[arg-type]
                },
                created_at=_iso(e.created_at),
            )
            for e in events
        ],
    )


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
    from arvel.activitylog import activity

    await (
        activity()
        .caused_by(user)
        .performed_on(order)
        .with_properties({"from": current.value, "to": target.value})
        .log("order status changed")
    )
    # Notify the customer when their order ships — QUEUED (database + mail channels), so the
    # committed transition never waits on (or 500s from) SMTP.
    if target is OrderStatus.SHIPPED and order.user_id is not None:
        customer = await User.find(order.user_id)
        if customer is not None:
            await customer.notify(OrderShippedNotification(order.id))
    return _order_out(order, await order.items().get())
