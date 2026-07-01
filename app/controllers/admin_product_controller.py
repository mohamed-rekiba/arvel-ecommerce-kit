"""Admin product CRUD — authorized via the Gate/ProductPolicy (only admins may mutate the catalog).

Exercises arvel's authorization (policies, user.can / AuthorizationError → 403/404), middleware
(token auth), and request validation. A denial renders as 403 (create) or 404 (update/delete,
deny_as_not_found). Typed end to end.
"""

from arvel import abort
from arvel.http import Request
from arvel.support import Str, current_user
from arvel.validation import ValidationException, Validator

from arvel.activitylog import activity

from app.enums import Permission, ProductStatus
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
    Translate,
    UpdateProductIn,
)


def _current_user() -> User:
    # The Authenticate route middleware guarantees a user is present (401'd otherwise).
    user = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    return user


async def _require_admin() -> User:
    """Reading the admin catalog needs catalog.view (mutations check catalog.create/update/delete)."""
    user = _current_user()
    if not await user.can(Permission.CATALOG_VIEW.value):
        abort(403, "You lack catalog access.")
    return user


async def products_index(
    request: Request, per_page: int = 20, page: int = 1
) -> AdminProductPage:
    """List **all** products (admin) — including hidden ones — each annotated with `is_visible`
    (the with_visibility scope adds the inline EXISTS column; one query for the page)."""
    await _require_admin()
    result = await Product.with_visibility().order_by("id").paginate(per_page, page)
    return AdminProductPage(
        data=[
            AdminProductOut(
                id=p.id,
                slug=p.slug,
                translations=p.translations,
                status=ProductStatus(p.status).value,
                published=bool(p.published),
                is_visible=bool(getattr(p, "is_visible", False)),
            )
            for p in result.items()
        ],
        current_page=result.current_page(),
        last_page=result.last_page(),
        per_page=result.per_page(),
        total=result.total(),
    )


async def categories_index(
    request: Request, per_page: int = 50, page: int = 1
) -> AdminCategoryPage:
    """List **all** categories (admin) with `is_visible` (inline EXISTS column)."""
    await _require_admin()
    result = await Category.with_visibility().order_by("id").paginate(per_page, page)
    return AdminCategoryPage(
        data=[
            AdminCategoryOut(
                id=c.id,
                slug=c.slug,
                translations=c.translations,
                parent_id=c.parent_id,
                published=bool(c.published),
                is_visible=bool(getattr(c, "is_visible", False)),
            )
            for c in result.items()
        ],
        current_page=result.current_page(),
        last_page=result.last_page(),
        per_page=result.per_page(),
        total=result.total(),
    )


def _admin_product_out(product: Product, *, is_visible: bool) -> AdminProductOut:
    return AdminProductOut(
        id=product.id,
        slug=product.slug,
        translations=product.translations,
        status=ProductStatus(product.status).value,
        published=bool(product.published),
        is_visible=is_visible,
    )


async def store(request: Request, data: ProductIn) -> AdminProductOut:
    """Create a product (admins only). The name/description are stored in the default (en) locale."""
    user = _current_user()
    if not await user.can("create", Product):
        abort(403, "Only admins may create products.")
    validator = Validator(
        {
            "category_id": data.category_id,
            "name": data.name,
            "price_cents": data.price_cents,
        },
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
        translations={"en": {"name": data.name, "description": data.description}},
        slug=Str.slug(data.name),
        price_cents=data.price_cents,
        currency="USD",
        status=ProductStatus.DRAFT,
    )
    await (
        activity()
        .caused_by(user)
        .performed_on(product)
        .with_properties({"name": data.name, "slug": product.slug})
        .log("created product")
    )
    return _admin_product_out(product, is_visible=False)  # a new draft is never visible


async def update(request: Request, data: UpdateProductIn) -> AdminProductOut:
    """Update a product (admins only; 404 to non-admins so existence isn't leaked)."""
    user = _current_user()
    product = await Product.find_or_fail(int(request.path_param("id")))
    if not await user.can("update", product):
        abort(404, "Product not found")
    if data.name is not None:  # update the en translation, preserving other locales
        existing: list[Translate] = product.translations
        current = {
            t.locale: {"name": t.name, "description": t.description} for t in existing
        }
        current["en"] = {
            "name": data.name,
            "description": current.get("en", {}).get("description"),
        }
        product.translations = current
    if data.price_cents is not None:
        product.price_cents = data.price_cents
    if data.status is not None:
        product.status = ProductStatus(data.status)
    await product.save()
    await (
        activity()
        .caused_by(user)
        .performed_on(product)
        .with_properties(
            {
                "changed": [
                    k
                    for k in ("name", "price_cents", "status")
                    if getattr(data, k) is not None
                ]
            }
        )
        .log("updated product")
    )
    refreshed = await Product.with_visibility().where("id", product.id).first_or_fail()
    return _admin_product_out(
        refreshed, is_visible=bool(getattr(refreshed, "is_visible", False))
    )


async def destroy(request: Request) -> MessageOut:
    """Delete a product (admins only; 404 to non-admins)."""
    user = _current_user()
    product = await Product.find_or_fail(int(request.path_param("id")))
    if not await user.can("delete", product):
        abort(404, "Product not found")
    await (
        activity()
        .caused_by(user)
        .performed_on(product)
        .with_properties({"slug": product.slug})
        .log("deleted product")
    )
    await product.delete()
    return MessageOut(message="Deleted.")
