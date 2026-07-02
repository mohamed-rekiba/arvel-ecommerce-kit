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
from app.models.product import SUPPORTED_LOCALES, Product
from app.models.user import User
from app.schemas import (
    AdminCategoryOut,
    AdminCategoryPage,
    AdminProductDetailOut,
    AdminProductOut,
    AdminProductPage,
    MessageOut,
    ProductIn,
    TranslationFieldsIn,
    UpdateProductIn,
    VariantOut,
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


def _validated_translations(
    payload: dict[str, "TranslationFieldsIn"] | None,
) -> dict[str, dict[str, str | None]] | None:
    """Locale-whitelist + shape-check a translations map; None passes through (no change)."""
    if payload is None:
        return None
    bad = [locale for locale in payload if locale not in SUPPORTED_LOCALES]
    if bad:
        raise ValidationException(
            {"translations": [f"Unsupported locale(s): {', '.join(sorted(bad))}."]}
        )
    if "en" not in payload:
        raise ValidationException(
            {"translations": ["English (en) content is required."]}
        )
    for locale, fields in payload.items():
        if not fields.name.strip():
            raise ValidationException(
                {"translations": [f"The {locale} name can't be empty."]}
            )
    return {
        locale: {"name": fields.name, "description": fields.description}
        for locale, fields in payload.items()
    }


async def show(request: Request) -> AdminProductDetailOut:
    """One product with variants + gallery — the editor's read (hidden products included)."""
    from app.controllers.catalog_controller import gallery_image_out
    from app.models.product_variant import ProductVariant

    await _require_admin()
    product = (
        await Product.with_visibility()
        .where("id", int(request.path_param("id")))
        .first_or_fail()
    )
    variants = await ProductVariant.where("product_id", product.id).order_by("id").get()
    from app.controllers.media_controller import IMAGES

    gallery = [gallery_image_out(m) for m in await product.get_media(IMAGES)]
    return AdminProductDetailOut(
        id=product.id,
        slug=product.slug,
        translations=product.translations,
        status=ProductStatus(product.status).value,
        published=bool(product.published),
        is_visible=bool(getattr(product, "is_visible", False)),
        price_cents=product.price_cents,
        category_id=product.category_id,
        variants=[
            VariantOut(
                id=v.id,
                sku=v.sku,
                name=v.name,
                price_adjustment_cents=v.price_adjustment_cents,
                stock=v.stock,
            )
            for v in variants
        ],
        gallery=gallery,
    )


async def store(request: Request, data: ProductIn) -> AdminProductOut:
    """Create a product (admins only) with per-locale content (en required)."""
    user = _current_user()
    if not await user.can("create", Product):
        abort(403, "Only admins may create products.")
    validator = Validator(
        {"category_id": data.category_id, "price_cents": data.price_cents},
        {"category_id": "required|integer", "price_cents": "required|integer|min:0"},
    )
    if validator.fails():
        raise ValidationException(validator.errors())
    translations = _validated_translations(data.translations)
    assert translations is not None  # ProductIn.translations is required
    product = await Product.create(
        category_id=data.category_id,
        translations=translations,
        slug=Str.slug(translations["en"]["name"] or ""),
        price_cents=data.price_cents,
        currency="USD",
        status=ProductStatus.DRAFT,
    )
    await (
        activity()
        .caused_by(user)
        .performed_on(product)
        .with_properties({"name": translations["en"]["name"], "slug": product.slug})
        .log("created product")
    )
    return _admin_product_out(product, is_visible=False)  # a new draft is never visible


async def update(request: Request, data: UpdateProductIn) -> AdminProductOut:
    """Update a product — per-locale content, price, category, status, visibility (admins only;
    404 to non-admins so existence isn't leaked)."""
    user = _current_user()
    product = await Product.find_or_fail(int(request.path_param("id")))
    if not await user.can("update", product):
        abort(404, "Product not found")
    translations = _validated_translations(data.translations)
    if translations is not None:
        product.translations = translations
    if data.category_id is not None:
        await Category.find_or_fail(data.category_id)  # 404 on a bogus category
        product.category_id = data.category_id
    if data.price_cents is not None:
        if data.price_cents < 0:
            raise ValidationException({"price_cents": ["The price can't be negative."]})
        product.price_cents = data.price_cents
    if data.status is not None:
        product.status = ProductStatus(data.status)
    if data.published is not None:
        product.published = data.published
    await product.save()
    if data.published is not None or data.status is not None:
        # visibility inputs changed → flag the retrievable views dirty (debounced refresh)
        from app.services.catalog_visibility_service import CatalogVisibilityService

        await CatalogVisibilityService.mark_dirty()
    await (
        activity()
        .caused_by(user)
        .performed_on(product)
        .with_properties(
            {
                "changed": [
                    k
                    for k in (
                        "translations",
                        "category_id",
                        "price_cents",
                        "status",
                        "published",
                    )
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
