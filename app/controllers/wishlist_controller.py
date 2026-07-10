"""Customer wishlist API — a signed-in customer's saved products (list + toggle). Bearer-guarded;
a customer only ever sees/edits their own saved items."""

from arvel import abort
from app.i18n import trans
from arvel.http import Request
from arvel.support import current_user

from typing import Any

from app.controllers.catalog_controller import product_out
from app.models.product import Product
from app.models.user import User
from app.models.wishlist_item import WishlistItem
from app.schemas import ProductOut, WishlistToggleOut


def _in_locale(query: Any) -> Any:
    return query.in_locale()


def _customer() -> User:
    user: User | None = current_user.get()
    if user is None:
        abort(401, trans("shop.errors.unauthenticated"))
    return user


async def index(request: Request) -> list[ProductOut]:
    """The signed-in customer's saved products (only ones still retrievable on the storefront)."""
    user = _customer()
    items = await WishlistItem.where("user_id", user.id).get()
    ids = [i.product_id for i in items]
    if not ids:
        return []
    products = (
        await Product.with_("product_variants", "media", category=_in_locale)
        .where_in("id", ids)
        .with_visibility(only_visible=True)
        .in_locale()
        .get()
    )
    return [await product_out(p) for p in products]


async def toggle(request: Request) -> WishlistToggleOut:
    """Add the product to the wishlist, or remove it if already saved."""
    user = _customer()
    product_id = int(request.path_param("product_id"))
    existing = (
        await WishlistItem.where("user_id", user.id)
        .where("product_id", product_id)
        .first()
    )
    if existing is not None:
        await existing.delete()
        return WishlistToggleOut(saved=False)
    await WishlistItem.create(user_id=user.id, product_id=product_id)
    return WishlistToggleOut(saved=True)
