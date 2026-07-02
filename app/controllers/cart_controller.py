"""Cart API — guest (by cart token) or authenticated (by user) carts.

Exercises arvel's ORM (relations, eager-load) + the Cache facade (the cart subtotal is cached and
invalidated on every mutation). Typed end to end: typed request bodies + a CartOut response schema.
A guest gets a cart token back on first add (echo it in `X-Cart-Token` next time); an authenticated
user's cart follows them.
"""

from arvel import Cache, abort
from arvel.http import Request
from arvel.support import Str, current_user
from arvel.validation import ValidationException

from app.models.cart import Cart
from app.models.coupon import Coupon
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.schemas import AddItemIn, ApplyCouponIn, CartLineOut, CartOut, UpdateItemIn


def _cart_total_key(cart_id: int) -> str:
    return f"cart:{cart_id}:total_cents"


async def resolve_cart(
    request: Request, *, create: bool
) -> tuple[Cart | None, str | None]:
    """Return (cart, new_token). For an authenticated user the cart follows the user; for a guest it
    is found by the `X-Cart-Token` header. `create` makes one when absent (returning its token for a
    guest so the client can send it next time)."""
    user = current_user.get()
    if user is not None:
        cart = await Cart.where("user_id", user.id).first()
        if cart is None and create:
            cart = await Cart.create(user_id=user.id)
        return cart, None
    token = request.header("x-cart-token")
    if token:
        cart = await Cart.where("token", token).first()
        if cart is not None:
            return cart, None
    if create:
        new_token = Str.random(40)
        cart = await Cart.create(token=new_token)
        return cart, new_token
    return None, None


async def merge_guest_cart(request: Request, user: User) -> None:
    """Fold the request's guest cart (X-Cart-Token) into ``user``'s cart — login/register call
    this so the classic build-a-cart-then-sign-in flow never strands items. Same variant in both →
    quantities sum, capped at available stock; distinct variants union; the guest cart is retired.
    A token that doesn't resolve to a genuine GUEST cart is ignored (nobody grafts a foreign or
    user-owned cart onto the authenticating account)."""
    token = request.header("x-cart-token")
    if not token:
        return
    guest = await Cart.where("token", token).first()
    if guest is None or guest.user_id is not None:
        return
    guest_items = await guest.items().get()
    cart = await Cart.where("user_id", user.id).first()
    if cart is None and guest_items:
        cart = await Cart.create(user_id=user.id)
    for item in guest_items:
        assert cart is not None  # created above when there are items
        existing = (
            await CartItem.where("cart_id", cart.id)
            .where("product_variant_id", item.product_variant_id)
            .first()
        )
        if existing is None:
            await CartItem.create(
                cart_id=cart.id,
                product_variant_id=item.product_variant_id,
                quantity=item.quantity,
                unit_price_cents=item.unit_price_cents,
            )
        else:
            variant = await ProductVariant.find(item.product_variant_id)
            total = existing.quantity + item.quantity
            # cap at available stock (checkout re-verifies under lock either way)
            existing.quantity = max(min(total, variant.stock) if variant else total, 1)
            await existing.save()
    await CartItem.where("cart_id", guest.id).delete()
    await guest.delete()
    await Cache.forget(_cart_total_key(guest.id))
    if cart is not None:
        await Cache.forget(_cart_total_key(cart.id))


async def _serialize(cart: Cart, new_token: str | None = None) -> CartOut:
    items = await cart.items().with_("variant").get()
    total = await Cache.remember(
        _cart_total_key(cart.id),
        300,
        lambda: sum(i.unit_price_cents * i.quantity for i in items),
    )
    discount = 0
    if cart.coupon_code:
        from app.services.coupon_service import discount_cents

        coupon = await Coupon.where("code", cart.coupon_code).first()
        if coupon is not None:
            discount = discount_cents(coupon, int(total))
    return CartOut(
        id=cart.id,
        items=[
            CartLineOut(
                id=i.id,
                product_variant_id=i.product_variant_id,
                quantity=i.quantity,
                unit_price_cents=i.unit_price_cents,
                line_total_cents=i.unit_price_cents * i.quantity,
            )
            for i in items
        ],
        total_cents=int(total),
        coupon_code=cart.coupon_code,
        discount_cents=discount,
        cart_token=new_token,
    )


async def show(request: Request) -> CartOut:
    """Show the current cart (an empty shell if none exists yet)."""
    cart, _ = await resolve_cart(request, create=False)
    if cart is None:
        return CartOut(
            id=None, items=[], total_cents=0, coupon_code=None, discount_cents=0
        )
    return await _serialize(cart)


async def add_item(request: Request, data: AddItemIn) -> CartOut:
    """Add a variant to the cart (or bump its quantity if already present)."""
    if data.quantity < 1:
        raise ValidationException({"quantity": ["Quantity must be at least 1."]})
    variant = await ProductVariant.find(data.product_variant_id)
    if variant is None:
        abort(404, "Product variant not found")
    product = await Product.find(variant.product_id)
    if product is None:
        abort(404, "Product not found")
    from app.services import deal_service

    unit_price = await deal_service.current_unit_price_cents(
        product.id, product.price_cents + variant.price_adjustment_cents
    )

    cart, new_token = await resolve_cart(request, create=True)
    assert cart is not None  # create=True always yields a cart
    existing = (
        await cart.items().where("product_variant_id", data.product_variant_id).first()
    )
    if existing is not None:
        existing.quantity = existing.quantity + data.quantity
        await existing.save()
    else:
        await CartItem.create(
            cart_id=cart.id,
            product_variant_id=data.product_variant_id,
            quantity=data.quantity,
            unit_price_cents=unit_price,
        )
    await Cache.forget(_cart_total_key(cart.id))  # invalidate the cached subtotal
    return await _serialize(cart, new_token)


async def update_item(request: Request, data: UpdateItemIn) -> CartOut:
    """Set a line's quantity (0 removes it)."""
    cart, _ = await resolve_cart(request, create=False)
    if cart is None:
        abort(404, "Cart not found")
    item = await CartItem.find(int(request.path_param("id")))
    if item is None or item.cart_id != cart.id:
        abort(404, "Item not found")
    if data.quantity <= 0:
        await item.delete()
    else:
        item.quantity = data.quantity
        await item.save()
    await Cache.forget(_cart_total_key(cart.id))
    return await _serialize(cart)


async def remove_item(request: Request) -> CartOut:
    """Remove a line from the cart."""
    cart, _ = await resolve_cart(request, create=False)
    if cart is None:
        abort(404, "Cart not found")
    item = await CartItem.find(int(request.path_param("id")))
    if item is None or item.cart_id != cart.id:
        abort(404, "Item not found")
    await item.delete()
    await Cache.forget(_cart_total_key(cart.id))
    return await _serialize(cart)


async def apply_coupon(request: Request, data: ApplyCouponIn) -> CartOut:
    """Attach a coupon to the cart with immediate validation (checkout re-validates
    authoritatively — a code can expire between apply and place-order)."""
    from app.services.coupon_service import normalize_code, validate_window_and_state

    cart, new_token = await resolve_cart(request, create=True)
    assert cart is not None
    items = await cart.items().get()
    subtotal = sum(i.unit_price_cents * i.quantity for i in items)
    code = normalize_code(data.code)
    coupon = await Coupon.where("code", code).first()
    validate_window_and_state(coupon, subtotal)
    cart.coupon_code = code
    await cart.save()
    return await _serialize(cart, new_token)


async def remove_coupon(request: Request) -> CartOut:
    cart, _ = await resolve_cart(request, create=False)
    if cart is None:
        return CartOut(
            id=None, items=[], total_cents=0, coupon_code=None, discount_cents=0
        )
    cart.coupon_code = None
    await cart.save()
    return await _serialize(cart)
