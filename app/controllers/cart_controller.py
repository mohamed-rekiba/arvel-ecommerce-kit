"""Cart API — guest (by cart token) or authenticated (by user) carts.

Exercises arvel's ORM (relations, eager-load), the Cache facade (the cart subtotal is cached and
invalidated on every mutation), and request handling. A guest gets a cart token back on first add
(echo it in the ``X-Cart-Token`` header on later calls); an authenticated user's cart follows them.
"""

from typing import Any

from arvel import Cache, Schema, abort
from arvel.support import Str, current_user

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.product_variant import ProductVariant


def _cart_total_key(cart_id: int) -> str:
    return f"cart:{cart_id}:total_cents"


class AddItem(Schema):
    product_variant_id: int
    quantity: int = 1


async def _resolve_cart(request, *, create: bool) -> tuple[Cart | None, str | None]:
    """Return (cart, new_token). For an authenticated user the cart follows the user; for a guest it
    is found by the ``X-Cart-Token`` header. ``create`` makes one when absent (returning its token
    for a guest so the client can send it next time)."""
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


async def _serialize(cart: Cart, new_token: str | None = None) -> dict[str, Any]:
    items = await cart.items().with_("variant").get()
    # the subtotal is cached per-cart; mutations forget the key so it recomputes lazily
    total = await Cache.remember(
        _cart_total_key(cart.id),
        300,
        lambda: sum(i.unit_price_cents * i.quantity for i in items),
    )
    body: dict[str, Any] = {
        "id": cart.id,
        "items": [
            {
                "id": i.id,
                "product_variant_id": i.product_variant_id,
                "quantity": i.quantity,
                "unit_price_cents": i.unit_price_cents,
                "line_total_cents": i.unit_price_cents * i.quantity,
            }
            for i in items
        ],
        "total_cents": total,
    }
    if new_token is not None:
        body["cart_token"] = new_token
    return body


async def show(request) -> Any:
    """GET /api/cart — the current cart (empty shell if none yet)."""
    cart, _ = await _resolve_cart(request, create=False)
    if cart is None:
        return {"id": None, "items": [], "total_cents": 0}
    return await _serialize(cart)


async def add_item(request, data: AddItem) -> Any:
    """POST /api/cart/items — add a variant (or bump its quantity if already in the cart)."""
    if data.quantity < 1:
        abort(422, {"quantity": ["Quantity must be at least 1."]})
    variant = await ProductVariant.find(data.product_variant_id)
    if variant is None:
        abort(404, "Product variant not found")
    product = await Product.find(variant.product_id)
    unit_price = product.price_cents + variant.price_adjustment_cents

    cart, new_token = await _resolve_cart(request, create=True)
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
    from arvel.http import Response

    return Response(content=await _serialize(cart, new_token), status=201)


async def update_item(request) -> Any:
    """PATCH /api/cart/items/{id} — set a line's quantity (0 removes it)."""
    cart, _ = await _resolve_cart(request, create=False)
    if cart is None:
        abort(404, "Cart not found")
    item = await CartItem.find(int(request.path_param("id")))
    if item is None or item.cart_id != cart.id:
        abort(404, "Item not found")
    data = await request.json()
    quantity = int(data.get("quantity", 0))
    if quantity <= 0:
        await item.delete()
    else:
        item.quantity = quantity
        await item.save()
    await Cache.forget(_cart_total_key(cart.id))
    return await _serialize(cart)


async def remove_item(request) -> Any:
    """DELETE /api/cart/items/{id} — remove a line."""
    cart, _ = await _resolve_cart(request, create=False)
    if cart is None:
        abort(404, "Cart not found")
    item = await CartItem.find(int(request.path_param("id")))
    if item is None or item.cart_id != cart.id:
        abort(404, "Item not found")
    await item.delete()
    await Cache.forget(_cart_total_key(cart.id))
    return await _serialize(cart)
