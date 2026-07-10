"""Checkout + orders — turn a cart into an order atomically, fire a domain event, and drive the
order state machine.
"""

from decimal import Decimal
from typing import Any

from arvel import DB, Cache, Event, abort
from arvel.http import Request
from arvel.support import Money, Str, current_user
from arvel.telemetry import span
from arvel.validation import ValidationException, Validator

from app.controllers.cart_controller import line_presentation, resolve_cart
from app.controllers.serializers import iso as _iso
from app.i18n import active_locale, trans
from app.controllers.order_access import resolve_owned_order
from app.enums import (
    CountryCode,
    Currency,
    OrderStatus,
    PaymentStatus,
    Permission,
    RefundStatus,
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
    RefundOut,
    ShippingMethodOut,
)

# Server-authoritative money rules (never trusted from the client): shipping rate, jurisdiction tax.


def _tax_cents(subtotal_cents: int, rate_bps: int) -> int:
    # Money.times rounds the minor units half-up (currency-correct) vs the old integer floor.
    # rate_bps is resolved server-side from the shipping country (tax_service) — never from the
    # request — and converted to Decimal only here, at the multiply (no floats in the money path).
    rate = Decimal(rate_bps) / Decimal(10000)
    return Money(subtotal_cents, Currency.USD.value).times(rate).amount


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


async def _latest_refund(order: Order) -> RefundOut | None:
    """The customer-facing summary of the most recent refund attempt (None = never refunded) —
    mirrors ``_latest_payment_status``'s minimal, id-free surface."""
    from app.models.refund import Refund

    refund = await Refund.where("order_id", order.id).order_by("id", "desc").first()
    if refund is None:
        return None
    status = (
        refund.status
        if isinstance(refund.status, RefundStatus)
        else RefundStatus(refund.status)
    )
    return RefundOut(
        amount_cents=refund.amount_cents,
        status=status,
        created_at=_iso(refund.created_at),
    )


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
    refund: RefundOut | None = None,
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
        shipping_method=order.shipping_method,
        tracking_number=order.tracking_number,
        items=[
            OrderLineOut(
                product_variant_id=i.product_variant_id,
                product_name=i.product_name,
                product_slug=looks.get(i.product_variant_id, ("", "", None, None))[3],
                variant_name=i.variant_name,
                image_url=looks.get(i.product_variant_id, ("", "", None, None))[2],
                quantity=i.quantity,
                unit_price_cents=i.unit_price_cents,
            )
            for i in items
        ],
        placed_at=_iso(getattr(order, "created_at", None)),
        timeline=timeline,
        refund=refund,
    )


async def _reprice_lines(items: list[Any]) -> None:
    """Re-derive every cart line's unit price at ORDER time (base + variant adjustment, with
    whatever deal is live right now) immediately before the order transaction opens — the cart
    snapshot is a quote; the order always charges today's price. Totals are server-computed."""
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
        errors["country"] = [
            trans("shop.errors.country_not_shipped", country=payload["country"])
        ]
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
        abort(422, trans("shop.errors.cart_empty"))
    items = await cart.items().get()
    if not items:
        abort(422, trans("shop.errors.cart_empty"))

    user = current_user.get()
    # a signed-in customer must have a verified email before placing an order; guest checkout
    # (no account) is unaffected
    if user is not None and not user.has_verified_email():
        abort(403, trans("shop.checkout.unverified_email"))
    # a newly-typed address (vs a saved one) gets added to the book below — capture the intent
    # before `data` is rebuilt from the saved entry
    new_address = (
        user is not None and data.address_id is None and data.address is not None
    )
    if data.address_id is not None:
        if user is None:
            abort(401, trans("shop.errors.signin_for_saved_address"))
        from app.models.address import Address

        saved = await Address.find(data.address_id)
        if saved is None or saved.user_id != user.id:
            abort(404, trans("shop.errors.address_not_found"))
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
            shipping_method=data.shipping_method,
        )
    contact_email, ship_fields = _validate_checkout(
        data, user.email if user is not None else None
    )
    await _reprice_lines(
        items
    )  # current-price-wins: stale deal snapshots never reach an order
    subtotal = sum(i.unit_price_cents * i.quantity for i in items)
    from app.services import shipping_service, tax_service

    # resolved from the client-selected CODE, never a client-sent rate — 422s (ValidationException)
    # before the transaction opens if the method is unknown/inactive, so no stock is ever locked.
    shipping = await shipping_service.resolve_rate_cents(data.shipping_method)

    # resolved ONCE from the server-validated ship_country — never a client-sent rate — and reused
    # for both the charge and the stored tax_rate_bps, so stored always matches charged.
    # ship_country is always set here (the Validator above requires "country"); the dict's value
    # type is a plain str | None because ship_line2 (the only optional address part) shares it.
    # Guard rather than assert — asserts strip under -O, and this is a money/tax path.
    ship_country = ship_fields["ship_country"]
    if ship_country is None:
        raise ValidationException({"ship_country": ["A shipping country is required."]})
    tax_rate_bps = await tax_service.resolve_rate_bps(ship_country)
    tax = _tax_cents(subtotal, tax_rate_bps)
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
                if coupon is None:
                    abort(500, "Coupon unexpectedly missing.")
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
                    abort(404, trans("shop.errors.variant_not_found"))
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
                shipping_method=data.shipping_method,
                tax_cents=tax,
                tax_rate_bps=tax_rate_bps,
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
                    abort(404, trans("shop.errors.product_not_found"))
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

            # save a first-time/new shipping address to the customer's book (first becomes default),
            # atomically with the order
            if new_address and user is not None:
                from app.controllers.address_controller import save_for

                name = ship_fields["ship_name"]
                line1 = ship_fields["ship_line1"]
                city = ship_fields["ship_city"]
                postal = ship_fields["ship_postal_code"]
                country = ship_fields["ship_country"]
                # required address parts are validated non-empty; the truthiness check both narrows
                # the shared str | None dict type and skips saving a blank entry
                if name and line1 and city and postal and country:
                    await save_for(
                        user,
                        name=name,
                        line1=line1,
                        line2=ship_fields["ship_line2"],
                        city=city,
                        postal_code=postal,
                        country=country,
                    )

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
    elif (
        OrderStatus.REFUNDED.value in reached
        or OrderStatus.REFUND_PENDING.value in reached
    ):
        # terminal money-returned branch (K15): show only the states actually reached and end at
        # the refund state — never grey out future shipped/delivered, the order isn't progressing
        # to delivery. Includes shipped only if it happened (a shipped return still refunds).
        terminal = (
            OrderStatus.REFUNDED
            if OrderStatus.REFUNDED.value in reached
            else OrderStatus.REFUND_PENDING
        )
        path = [
            step
            for step in (OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.SHIPPED)
            if step.value in reached
        ]
        path.append(terminal)
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
        refund=await _latest_refund(order),
    )


async def cancel(request: Request) -> OrderOut:
    """Cancel the order (owner or token holder) while the state machine allows it. A PENDING
    (unpaid) cancel is a plain, synchronous CANCELLED + restock — unchanged. A PAID cancel is a
    REFUND (K15, DR-0065): money was captured, so it must come back — the customer keeps ONE
    action, routed to `refund_service.initiate_refund` (the same function the admin refund route
    uses). This first read is unlocked and only picks which path to take; each path re-validates
    the real state under its own `FOR UPDATE` before doing anything irreversible, so a race here
    (e.g. the order ships between this read and the lock) is caught by that path's own guard, not
    by this dispatch."""
    order = await resolve_owned_order(request, int(request.path_param("id")))
    current = (
        order.status
        if isinstance(order.status, OrderStatus)
        else OrderStatus(order.status)
    )
    if current is OrderStatus.PAID:
        from app.services.refund_service import initiate_refund

        refund = await initiate_refund(order)
        refunded = await Order.find(refund.order_id)
        if refunded is None:
            abort(404, trans("shop.errors.order_not_found"))
        return await _order_out(
            refunded,
            await refunded.items().get(),
            payment_status=await _latest_payment_status(refunded),
            refund=await _latest_refund(refunded),
        )
    async with DB.transaction():
        # re-read under FOR UPDATE: two concurrent cancels serialize here, so exactly one
        # transitions and restocks — the loser sees CANCELLED and 422s
        locked = await Order.where("id", order.id).lock_for_update().first()
        if locked is None:
            abort(404, trans("shop.errors.order_not_found"))
        current = (
            locked.status
            if isinstance(locked.status, OrderStatus)
            else OrderStatus(locked.status)
        )
        if not can_transition(current, OrderStatus.CANCELLED):
            raise ValidationException(
                {
                    "order": [
                        trans("shop.errors.order_not_cancellable", status=current.value)
                    ]
                },
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
        abort(401, trans("shop.errors.unauthenticated"))
    orders = await Order.where("user_id", user.id).order_by("id", "desc").get()
    return [await _order_out(o, await o.items().get()) for o in orders]


async def admin_orders_index(request: Request) -> list[OrderOut]:
    """List orders (newest first) for the back office, narrowed by ``?status=`` and searched
    by ``?q=`` (order id, or a case-insensitive contact-email fragment). Requires orders.view."""
    user = current_user.get()
    if user is None or not await user.can(Permission.ORDERS_VIEW.value):
        abort(403, trans("shop.errors.no_orders_view"))
    query = Order.order_by("id", "desc")
    status = str(request.query("status", "") or "")
    if status:
        try:
            query = query.where("status", OrderStatus(status).value)
        except ValueError:
            abort(422, trans("shop.errors.unknown_status", status=status))
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


async def admin_order_show(request: Request, id: Order) -> AdminOrderDetailOut:
    """Everything a staff member needs on one order: lines (purchase snapshots), breakdown,
    address + contact, the customer link (or guest label), payment + webhook-backed states, and
    the transition history from the activity trail. Requires orders.view."""
    from arvel.activitylog import Activity

    from app.controllers.serializers import iso as _iso
    from app.enums import PaymentStatus as _PS
    from app.enums import RefundStatus as _RS
    from app.models.payment import Payment
    from app.models.refund import Refund
    from app.schemas import (
        AdminOrderCustomerOut,
        AdminOrderDetailOut,
        AdminOrderEventOut,
        AdminOrderPaymentOut,
        AdminOrderRefundOut,
    )

    # orders.view is enforced by the route's Authorize middleware (DR-0055) — it runs before
    # binding, so a denied caller gets a uniform 403 whether or not the order id exists.
    order = id
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
    refunds = await Refund.where("order_id", order.id).order_by("id").get()
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
        shipping_method=order.shipping_method,
        tracking_number=order.tracking_number,
        customer=customer,
        items=[
            OrderLineOut(
                product_variant_id=i.product_variant_id,
                product_name=i.product_name,
                product_slug=looks.get(i.product_variant_id, ("", "", None, None))[3],
                variant_name=i.variant_name,
                image_url=looks.get(i.product_variant_id, ("", "", None, None))[2],
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
        refunds=[
            AdminOrderRefundOut(
                id=r.id,
                gateway_charge_id=r.gateway_charge_id,
                gateway_refund_id=r.gateway_refund_id,
                amount_cents=r.amount_cents,
                status=r.status if isinstance(r.status, _RS) else _RS(r.status),
                restock=r.restock,
                created_at=_iso(r.created_at),
            )
            for r in refunds
        ],
        history=[
            AdminOrderEventOut(
                description=e.description,
                causer_id=e.causer_id,
                properties={
                    str(k): str(v) for k, v in dict(e.properties or {}).items()
                },
                created_at=_iso(e.created_at),
            )
            for e in events
        ],
    )


async def update_status(request: Request, id: Order, data: OrderStatusIn) -> OrderOut:
    """Transition an order, enforcing the state machine. orders.update is enforced by the route's
    Authorize middleware (DR-0055), so a denied caller 403s uniformly whether or not the id exists."""
    user = current_user.get()
    if user is None:
        abort(
            401, trans("shop.errors.unauthenticated")
        )  # unreachable post-Authorize; keeps `user` narrowed below
    order = id
    try:
        target = OrderStatus(data.status)
    except ValueError:
        raise ValidationException(
            {"status": [trans("shop.errors.unknown_status", status=data.status)]}
        ) from None
    current = (
        order.status
        if isinstance(order.status, OrderStatus)
        else OrderStatus(order.status)
    )
    if (
        OrderStatus.REFUND_PENDING in (target, current)
        or target is OrderStatus.REFUNDED
    ):
        # Money-moving states MUST go through refund_service, in BOTH directions:
        #   - target REFUND_PENDING/REFUNDED: only refund_service.initiate_refund /
        #     the charge.refunded webhook may CREATE the Refund row + call the gateway + restock —
        #     this endpoint only ever flips the status column.
        #   - current REFUND_PENDING: REFUND_PENDING -> PAID exists in ORDER_TRANSITIONS ONLY for
        #     refund_service's own synchronous reverse-call-failure recovery. Without this check
        #     that edge was reachable here too (target="paid" isn't itself a rejected target), so
        #     an admin could flip an order with a reverse charge already in flight straight to
        #     PAID — the order reads fulfillable, the Refund row is orphaned PENDING forever (the
        #     later charge.refunded webhook finds a non-REFUND_PENDING order and no-ops), and the
        #     merchant both ships the goods AND has refunded the money. REFUND_PENDING is exited
        #     ONLY by refund_service (webhook success -> REFUNDED, sync failure -> PAID) — never
        #     by this generic route, regardless of target.
        # REFUNDED is terminal in ORDER_TRANSITIONS anyway (can_transition below would already
        # 422 any target from it), but the target-is-REFUNDED check above catches it earlier with
        # the clearer message.
        raise ValidationException(
            {"status": [trans("shop.errors.use_refund_endpoint")]}
        )
    if not can_transition(
        current, target, cod=_method_value(order) is PaymentMethod.COD
    ):
        raise ValidationException(
            {
                "status": [
                    trans(
                        "shop.errors.invalid_transition",
                        from_status=current.value,
                        to_status=target.value,
                    )
                ]
            }
        )
    if target is OrderStatus.SHIPPED:
        # a tracking number is required to ship — the customer needs a way to follow the parcel;
        # stored BEFORE save() so the mail/db notification below reads the persisted value.
        tracking = (data.tracking_number or "").strip()
        if not tracking:
            raise ValidationException(
                {"tracking_number": ["A tracking number is required to ship an order."]}
            )
        order.tracking_number = tracking
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
            await customer.notify(
                OrderShippedNotification(order.id, order.tracking_number)
            )
    return await _order_out(order, await order.items().get())


async def admin_refund(request: Request, id: Order) -> OrderOut:
    """Admin-issued refund/return (K15): PAID (a support cancel) or SHIPPED (the one documented
    return case) -> REFUND_PENDING via the same `refund_service.initiate_refund` the customer
    /cancel route uses — one money-moving code path, two entry points. orders.update is enforced
    by the route's Authorize middleware (DR-0055), so a denied caller 403s uniformly whether or
    not the id exists."""
    from app.services.refund_service import initiate_refund

    refund = await initiate_refund(id)
    order = await Order.find(refund.order_id)
    if order is None:
        abort(404, trans("shop.errors.order_not_found"))
    return await _order_out(
        order,
        await order.items().get(),
        payment_status=await _latest_payment_status(order),
        refund=await _latest_refund(order),
    )


async def shipping_methods(request: Request) -> list[ShippingMethodOut]:
    """The active shipping methods + their server rate, for the checkout method selector."""
    from app.services import shipping_service

    return [
        ShippingMethodOut(code=m.code, name=m.name, rate_cents=m.rate_cents)
        for m in await shipping_service.list_methods()
    ]
