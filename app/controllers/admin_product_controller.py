"""Admin product CRUD — authorized via the Gate/ProductPolicy (only admins may mutate the catalog).

Exercises arvel's authorization (policies, user.can / AuthorizationError → 403/404), middleware
(token auth), and request validation. A denial renders as 403 (create) or 404 (update/delete,
deny_as_not_found). Typed end to end.
"""

from arvel import abort
from arvel.http import Request
from arvel.support import Str, current_user
from arvel.validation import ValidationException, Validator

from app.controllers.catalog_controller import product_out
from app.enums import ProductStatus
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.schemas import (
    AdminCategoryOut,
    AdminCategoryPage,
    AdminProductOut,
    AdminProductPage,
    MessageOut,
    ProductIn,
    ProductOut,
    UpdateProductIn,
)
from app.services.catalog_visibility_service import CatalogVisibilityService


def _current_user() -> User:
    # The Authenticate route middleware guarantees a user is present (401'd otherwise).
    user = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    return user


async def _require_admin() -> User:
    user = _current_user()
    if not await user.can("create", Product):  # the catalog-write gate == admin-only
        abort(403, "Admins only.")
    return user


async def products_index(request: Request, per_page: int = 20, page: int = 1) -> AdminProductPage:
    """List **all** products (admin) — including hidden ones — each annotated with `is_visible`
    (whether the storefront currently shows it)."""
    await _require_admin()
    result = await Product.order_by("id").paginate(per_page, page)
    items = result.items()
    visible = await CatalogVisibilityService.visible_product_ids_among([p.id for p in items])
    return AdminProductPage(
        data=[
            AdminProductOut(
                id=p.id,
                name=p.name,
                slug=p.slug,
                status=ProductStatus(p.status).value,
                published=bool(p.published),
                is_visible=p.id in visible,
            )
            for p in items
        ],
        current_page=result.current_page(),
        last_page=result.last_page(),
        per_page=result.per_page(),
        total=result.total(),
    )


async def categories_index(request: Request, per_page: int = 50, page: int = 1) -> AdminCategoryPage:
    """List **all** categories (admin) with `is_visible`."""
    await _require_admin()
    result = await Category.order_by("id").paginate(per_page, page)
    items = result.items()
    visible = await CatalogVisibilityService.visible_category_ids_among([c.id for c in items])
    return AdminCategoryPage(
        data=[
            AdminCategoryOut(
                id=c.id,
                name=c.name,
                slug=c.slug,
                parent_id=c.parent_id,
                published=bool(c.published),
                is_visible=c.id in visible,
            )
            for c in items
        ],
        current_page=result.current_page(),
        last_page=result.last_page(),
        per_page=result.per_page(),
        total=result.total(),
    )


async def store(request: Request, data: ProductIn) -> ProductOut:
    """Create a product (admins only)."""
    user = _current_user()
    if not await user.can("create", Product):
        abort(403, "Only admins may create products.")
    validator = Validator(
        {"category_id": data.category_id, "name": data.name, "price_cents": data.price_cents},
        {
            "category_id": "required|integer",
            "name": "required|string",
            "price_cents": "required|integer|min:0",
        },
    )
    if validator.fails():
        raise ValidationException(validator.errors())
    product = await Product.create(
        category_id=data.category_id,
        name=data.name,
        slug=Str.slug(data.name),
        price_cents=data.price_cents,
        currency="USD",
        status=ProductStatus.DRAFT,
    )
    return await product_out(product)


async def update(request: Request, data: UpdateProductIn) -> ProductOut:
    """Update a product (admins only; 404 to non-admins so existence isn't leaked)."""
    user = _current_user()
    product = await Product.find_or_fail(int(request.path_param("id")))
    if not await user.can("update", product):
        abort(404, "Product not found")
    if data.name is not None:
        product.name = data.name
    if data.price_cents is not None:
        product.price_cents = data.price_cents
    if data.status is not None:
        product.status = ProductStatus(data.status)
    await product.save()
    return await product_out(product)


async def destroy(request: Request) -> MessageOut:
    """Delete a product (admins only; 404 to non-admins)."""
    user = _current_user()
    product = await Product.find_or_fail(int(request.path_param("id")))
    if not await user.can("delete", product):
        abort(404, "Product not found")
    await product.delete()
    return MessageOut(message="Deleted.")
