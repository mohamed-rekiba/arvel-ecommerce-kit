"""Checkout + orders — turn a cart into an order atomically, fire a domain event, and drive the
order state machine. Typed end to end (request, response schemas).

Exercises arvel's DB transactions (DB.transaction — order + items created and the cart cleared
atomically; a failure rolls all of it back), events (Event.dispatch('order.placed') → the registered
listener), telemetry (a checkout span), and the typed OrderStatus state machine (app.enums).
"""

from typing import Any

from arvel import DB, Cache, Event, abort
from arvel.http import Request
from arvel.support import Str, current_user
from arvel.telemetry import span
from arvel.validation import ValidationException, Validator

from app.controllers.cart_controller import line_presentation, resolve_cart
from app.controllers.serializers import iso as _iso
from app.i18n import active_locale
from app.controllers.order_access import resolve_owned_order
from app.enums import (
    CountryCode,
    Currency,
    OrderStatus,
    PaymentStatus,
    Permission,
    can_transition,
    PaymentMethod,
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
    AddressIn,
    AddressOut,
    AdminOrderDetailOut,
    CheckoutIn,
    MetricsOut,
    OrderLineOut,
    OrderOut,
    OrderStatusIn,
    OrderTimelineOut,
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


async def log_transition(order: Order, before: OrderStatus, after: OrderStatus) -> None:
    """Every status change lands in the activity trail — the admin history AND the customer's
    tracking timeline read from it."""
    from arvel.activitylog import activity

    await (
        activity()
        .performed_on(order)
        .with_properties({"from": before.value, "to": after.value})
        .log("order status changed")
    )


def _method_value(order: Order) -> PaymentMethod:
    raw = getattr(order, "payment_method", None) or PaymentMethod.GATEWAY.value
    return raw if isinstance(raw, PaymentMethod) else PaymentMethod(raw)


async def _order_out(
    order: Order,
    items: list[OrderItem],
    payment_status: PaymentStatus | None = None,
    timeline: list[OrderTimelineOut] | None = None,
) -> OrderOut:
    looks = await line_presentation([i.product_variant_id for i in items])
    return OrderOut(
        id=order.id,
        status=_status_value(order),
        token=order.token,
        contact_email=order.contact_email,
        address=_address_out(order),
        subtotal_cents=order.subtotal_cents,
        shipping_cents=order.shipping_cents,
        tax_cents=order.tax_cents,
        coupon_code=order.coupon_code,
        discount_cents=order.discount_cents or 0,
        total_cents=order.total_cents,
        currency=_currency_value(order),
        payment_method=_method_value(order),
        payment_status=payment_status,
        items=[
            OrderLineOut(
                product_variant_id=i.product_variant_id,
                product_name=i.product_name,
                variant_name=i.variant_name,
                image_url=looks.get(i.product_variant_id, ("", "", None))[2],
                quantity=i.quantity,
                unit_price_cents=i.unit_price_cents,
            )
            for i in items
        ],
        placed_at=_iso(getattr(order, "created_at", None)),
        timeline=timeline,
    )


async def _reprice_lines(items: list[Any]) -> None:
    """Re-derive every cart line's unit price at ORDER time (base + variant adjustment, with the
    deal live right now applied), immediately BEFORE the order transaction opens. The cart
    snapshot is a quote; the order charges today's price — an expired deal is dropped, a deal
    that started after carting is honored (deal_service owns the math). A deal flipping in the
    microseconds between this re-price and the commit keeps the just-quoted price; totals are
    always server-computed."""
    from app.services import deal_service

    variants = {
        v.id: v
        for v in await ProductVariant.where_in(
            "id", [i.product_variant_id for i in items]
        ).get()
    }
    product_ids = list({v.product_id for v in variants.values()})
    products = {p.id: p for p in await Product.where_in("id", product_ids).get()}
    deals = await deal_service.active_deals_for(product_ids)
    for item in items:
        variant = variants.get(item.product_variant_id)
        if variant is None:
            continue  # the stock loop below 404s/409s dead lines with better messages
        product = products.get(variant.product_id)
        if product is None:
            continue
        base = product.price_cents + variant.price_adjustment_cents
        deal = deals.get(product.id)
        item.unit_price_cents = (
            deal_service.deal_price_cents(base, deal) if deal is not None else base
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
    if data.address_id is not None:
        if user is None:
            abort(401, "Sign in to use a saved address.")
        from app.models.address import Address

        saved = await Address.find(data.address_id)
        if saved is None or saved.user_id != user.id:
            abort(404, "Address not found")
        data = CheckoutIn(
            email=data.email,
            address=AddressIn(
                name=saved.name,
                line1=saved.line1,
                line2=saved.line2,
                city=saved.city,
                postal_code=saved.postal_code,
                country=saved.country,
            ),
            payment_method=data.payment_method,
        )
    contact_email, ship_fields = _validate_checkout(
        data, user.email if user is not None else None
    )
    await _reprice_lines(
        items
    )  # current-price-wins: stale deal snapshots never reach an order
    subtotal = sum(i.unit_price_cents * i.quantity for i in items)
    shipping = _shipping_cents(subtotal)
    tax = _tax_cents(subtotal)
    total = (
        subtotal + shipping + tax
    )  # a cart coupon is re-validated + applied inside the tx

    # a business span over the whole checkout — the DB queries inside auto-nest under it.
    with span(
        "checkout.place_order",
        attributes={"checkout.total_cents": total, "checkout.line_count": len(items)},
    ):
        async with DB.transaction():
            # Re-validate + redeem the cart's coupon UNDER A ROW LOCK: two checkouts racing for a
            # code's last use serialize here, so exactly one redeems (usage counted transactionally).
            discount = 0
            coupon = None
            if cart.coupon_code:
                from app.models.coupon import Coupon
                from app.services.coupon_service import (
                    discount_cents,
                    enforce_per_customer_limit,
                    validate_window_and_state,
                )

                coupon = (
                    await Coupon.where("code", cart.coupon_code)
                    .lock_for_update()
                    .first()
                )
                validate_window_and_state(coupon, subtotal)
                assert coupon is not None
                await enforce_per_customer_limit(
                    coupon,
                    user_id=user.id if user is not None else None,
                    contact_email=contact_email,
                )
                discount = discount_cents(coupon, subtotal)
                coupon.uses = (coupon.uses or 0) + 1
                await coupon.save()
                total = subtotal - discount + shipping + tax

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
                payment_method=data.payment_method.value,
                token=Str.random(40),
                contact_email=contact_email,
                coupon_code=cart.coupon_code,
                discount_cents=discount,
                subtotal_cents=subtotal,
                shipping_cents=shipping,
                tax_cents=tax,
                total_cents=total,
                currency=Currency.USD,
                **ship_fields,
            )
            if coupon is not None:
                from app.models.coupon_redemption import CouponRedemption

                await CouponRedemption.create(
                    coupon_id=coupon.id,
                    order_id=order.id,
                    user_id=user.id if user is not None else None,
                    contact_email=contact_email,
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
            locale=active_locale(),
        ),
    )
    return await _order_out(order, order_items)


async def _timeline(order: Order) -> list[OrderTimelineOut]:
    """The customer-facing tracking stepper: placed (created_at) + every status change from the
    activity trail. Steps not reached yet are emitted with at=None so the UI can grey them."""
    from arvel.activitylog import Activity

    from app.controllers.serializers import iso as _iso

    events = (
        await Activity.where("subject_type", "Order")
        .where("subject_id", order.id)
        .order_by("id")
        .get()
    )
    reached: dict[str, str | None] = {
        OrderStatus.PENDING.value: _iso(getattr(order, "created_at", None))
    }
    for event in events:
        props = dict(event.properties or {})
        target = props.get("to")
        if event.description == "order status changed" and target:
            reached[str(target)] = _iso(event.created_at)
    if OrderStatus.CANCELLED.value in reached:
        path = [OrderStatus.PENDING, OrderStatus.CANCELLED]
    elif _method_value(order) is PaymentMethod.COD:
        path = [OrderStatus.PENDING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]
    else:
        path = [
            OrderStatus.PENDING,
            OrderStatus.PAID,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ]
    return [OrderTimelineOut(status=step, at=reached.get(step.value)) for step in path]


async def show(request: Request) -> OrderOut:
    """One order, with lines + breakdown + the tracking timeline — for the signed-in owner or
    the order-token holder."""
    order = await resolve_owned_order(request, int(request.path_param("id")))
    return await _order_out(
        order,
        await order.items().get(),
        payment_status=await _latest_payment_status(order),
        timeline=await _timeline(order),
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
        before = (
            locked.status
            if isinstance(locked.status, OrderStatus)
            else OrderStatus(locked.status)
        )
        locked.status = OrderStatus.CANCELLED
        await locked.save()
        await log_transition(locked, before, OrderStatus.CANCELLED)
    return await _order_out(
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
    return [await _order_out(o, await o.items().get()) for o in orders]


async def admin_orders_index(request: Request) -> list[OrderOut]:
    """List orders (newest first) for the back office, narrowed by ``?status=`` and searched
    by ``?q=`` (order id, or a case-insensitive contact-email fragment). Requires orders.view."""
    user = current_user.get()
    if user is None or not await user.can(Permission.ORDERS_VIEW.value):
        abort(403, "You may not view orders.")
    query = Order.order_by("id", "desc")
    status = str(request.query("status", "") or "")
    if status:
        try:
            query = query.where("status", OrderStatus(status).value)
        except ValueError:
            abort(422, f"Unknown status '{status}'")
    q = str(request.query("q", "") or "").strip()
    if q:
        if q.isdigit():
            query = query.where("id", int(q))
        else:
            # escape LIKE metacharacters so a literal % or _ in the search stays literal
            safe = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where("contact_email", "ilike", f"%{safe}%")
    orders = await query.get()
    return [await _order_out(o, await o.items().get()) for o in orders]


async def admin_order_show(request: Request) -> AdminOrderDetailOut:
    """Everything a staff member needs on one order: lines (purchase snapshots), breakdown,
    address + contact, the customer link (or guest label), payment + webhook-backed states, and
    the transition history from the activity trail. Requires orders.view."""
    from arvel.activitylog import Activity

    from app.controllers.serializers import iso as _iso
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
    looks = await line_presentation([i.product_variant_id for i in items])

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

    return AdminOrderDetailOut(
        id=order.id,
        status=_status_value(order),
        contact_email=order.contact_email,
        address=_address_out(order),
        subtotal_cents=order.subtotal_cents,
        shipping_cents=order.shipping_cents,
        tax_cents=order.tax_cents,
        coupon_code=order.coupon_code,
        discount_cents=order.discount_cents,
        total_cents=order.total_cents,
        currency=_currency_value(order),
        payment_method=_method_value(order),
        customer=customer,
        items=[
            OrderLineOut(
                product_variant_id=i.product_variant_id,
                product_name=i.product_name,
                variant_name=i.variant_name,
                image_url=looks.get(i.product_variant_id, ("", "", None))[2],
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
    if not can_transition(
        current, target, cod=_method_value(order) is PaymentMethod.COD
    ):
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
    return await _order_out(order, await order.items().get())
