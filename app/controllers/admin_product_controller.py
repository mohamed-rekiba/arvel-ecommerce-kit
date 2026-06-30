"""Admin product CRUD — authorized via the Gate/ProductPolicy (only admins may mutate the catalog).

Exercises arvel's authorization (policies, user.can / AuthorizationError → 403/404), middleware
(token auth), and request validation. The authenticated user is resolved from the bearer token, then
the policy decides; a denial renders as 403 (create) or 404 (update/delete, deny_as_not_found).
"""

from typing import Any

from arvel import Schema, abort
from arvel.support import Str, current_user
from arvel.validation import Validator

from app.enums import ProductStatus
from app.models.product import Product
from app.models.user import User


class ProductInput(Schema):
    category_id: int
    name: str
    price_cents: int


def _current_user() -> User:
    # The Authenticate route middleware guarantees a user is present (401'd otherwise).
    user = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    return user


async def store(request, data: ProductInput) -> Any:
    """POST /api/admin/products — create a product (admins only)."""
    user = _current_user()
    if not await user.can("create", Product):
        abort(403, "Only admins may create products.")
    payload = {"category_id": data.category_id, "name": data.name, "price_cents": data.price_cents}
    validator = Validator(
        payload,
        {
            "category_id": "required|integer",
            "name": "required|string",
            "price_cents": "required|integer|min:0",
        },
    )
    if validator.fails():
        abort(422, validator.errors())
    product = await Product.create(
        category_id=data.category_id,
        name=data.name,
        slug=Str.slug(data.name),
        price_cents=data.price_cents,
        currency="USD",
        status=ProductStatus.DRAFT,
    )
    from arvel.http import Response

    return Response(content=product.to_dict(), status=201)


async def update(request) -> Any:
    """PUT /api/admin/products/{id} — update a product (admins only; 404 to non-admins)."""
    user = _current_user()
    product = await Product.find(int(request.path_param("id")))
    if product is None:
        abort(404, "Product not found")
    # policy.update denies non-admins AS 404 (deny_as_not_found) — don't leak existence
    if not await user.can("update", product):
        abort(404, "Product not found")
    data = await request.json()
    if "name" in data:
        product.name = data["name"]
    if "price_cents" in data:
        product.price_cents = data["price_cents"]
    if "status" in data:
        product.status = ProductStatus(data["status"])
    await product.save()
    return product


async def destroy(request) -> Any:
    """DELETE /api/admin/products/{id} — delete a product (admins only; 404 to non-admins)."""
    user = _current_user()
    product = await Product.find(int(request.path_param("id")))
    if product is None:
        abort(404, "Product not found")
    if not await user.can("delete", product):
        abort(404, "Product not found")
    await product.delete()
    from arvel.http import Response

    return Response(content={"message": "Deleted."}, status=200)
