"""Admin product CRUD — authorized via the Gate/ProductPolicy (only admins may mutate the catalog).

A denial renders as 403 on create, 404 on update/delete/restore (existence isn't leaked, per
deny_as_not_found). Product is the only converted resource wired through
``authorize_resource`` (K5/DR-0056): it's the only one with a per-object policy, and that
policy already denies-as-404 on update/delete, so the in-handler guard stays uniform against a
binding-miss (K4/DR-0054). The other admin resources have no policy and stay on class-level
``Authorize`` middleware instead — see the sibling controllers.
"""

from typing import Any

from arvel import abort
from arvel.auth.middleware import Authorize
from arvel.http import Request
from arvel.routing import Controller, ControllerMiddleware
from arvel.support import Str, current_user
from arvel.validation import ValidationException, Validator

from arvel.activitylog import activity

from app.enums import Permission, ProductStatus
from app.i18n import SUPPORTED_LOCALES, active_locale, trans
from app.models.media import AppMedia
from app.models.category import Category
from app.models.product import IMAGES, Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.schemas import (
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
    user: User | None = current_user.get()
    if user is None:
        abort(401, trans("shop.errors.unauthenticated"))
    return user


_SORTS: dict[str, tuple[str, str]] = {
    "price_asc": ("price_cents", "asc"),
    "price_desc": ("price_cents", "desc"),
    "oldest": ("id", "asc"),
    "newest": ("id", "desc"),
}


def _page(
    result: Any, *, is_visible: bool | None = None, extras: dict[int, Any]
) -> AdminProductPage:
    return AdminProductPage(
        data=[
            _admin_product_out(
                p,
                is_visible=is_visible
                if is_visible is not None
                else bool(getattr(p, "is_visible", False)),
                extras=extras,
            )
            for p in result.items()
        ],
        current_page=result.current_page(),
        last_page=result.last_page(),
        per_page=result.per_page(),
        total=result.total(),
    )


async def _list_extras(ids: list[int]) -> dict[int, dict[str, Any]]:
    """Batch the per-row list extras (one query each): summed stock, variant count, first thumb URL."""
    extras: dict[int, dict[str, Any]] = {
        pid: {"stock": 0, "variants": 0, "thumb": None} for pid in ids
    }
    if not ids:
        return extras
    for v in await ProductVariant.where_in("product_id", ids).get():
        row = extras.get(v.product_id)
        if row is not None:
            row["stock"] += int(v.stock or 0)
            row["variants"] += 1
    seen: set[int] = set()
    media = (
        await AppMedia.where("model_type", "Product")
        .where_in("model_id", ids)
        .where("collection_name", IMAGES)
        .order_by("id")
        .get()
    )
    for m in media:
        if m.model_id in seen:
            continue
        seen.add(m.model_id)
        row = extras.get(m.model_id)
        if row is not None:
            row["thumb"] = m.serving_url("thumb")
    return extras


def _admin_product_out(
    product: Product, *, is_visible: bool, extras: dict[int, Any] | None = None
) -> AdminProductOut:
    row = (extras or {}).get(product.id, {})
    return AdminProductOut(
        id=product.id,
        slug=product.slug,
        translations=product.translations,
        status=ProductStatus(product.status).value,
        published=bool(product.published),
        featured=bool(getattr(product, "featured", False)),
        is_visible=is_visible,
        price_cents=int(getattr(product, "price_cents", 0) or 0),
        currency=str(getattr(product, "currency", "USD") or "USD"),
        image_url=row.get("thumb"),
        stock=int(row.get("stock", 0)),
        variant_count=int(row.get("variants", 0)),
    )


def validated_translations(
    payload: dict[str, "TranslationFieldsIn"] | None,
) -> dict[str, dict[str, str | None]] | None:
    """Locale-whitelist + shape-check a translations map; None passes through (no change)."""
    if payload is None:
        return None
    bad = [locale for locale in payload if locale not in SUPPORTED_LOCALES]
    if bad:
        raise ValidationException(
            {
                "translations": [
                    trans(
                        "shop.errors.unsupported_locales",
                        locales=", ".join(sorted(bad)),
                    )
                ]
            }
        )
    if "en" not in payload:
        raise ValidationException(
            {"translations": [trans("shop.errors.english_required")]}
        )
    for locale, fields in payload.items():
        if not fields.name.strip():
            raise ValidationException(
                {
                    "translations": [
                        trans("shop.errors.translation_name_empty", lang=locale)
                    ]
                }
            )
    return {
        locale: {"name": fields.name, "description": fields.description}
        for locale, fields in payload.items()
    }


class AdminProductController(Controller):
    """The five admin product CRUD actions. index/show carry a declared ``Authorize(CATALOG_VIEW)``
    (``ProductPolicy.view``/``viewAny`` are public no-ops — the storefront contract — so without
    this middleware admin listing would be wide open); store/update/destroy carry no middleware of
    their own because ``authorize_resource(Product)`` below already guards them against the policy
    (create→403, update/delete→404) — declaring both would be double-enforcement for no benefit
    (K5/DR-0056). ``update`` registers through this class's normal ``Router.resource()`` wiring —
    it used to be pulled out into an explicit PUT-only route because arvel's resource generator
    bound it to both PUT and PATCH under one route name, tripping Litestar's
    one-operationId-per-operation OpenAPI check; that's fixed at the framework level now
    (DR-0057), so `update` needs no carve-out and accepts both verbs like a normal resource
    action."""

    @classmethod
    def middleware(cls) -> list[ControllerMiddleware]:
        return [
            ControllerMiddleware(
                Authorize(Permission.CATALOG_VIEW.value), only=("index", "show")
            ),
        ]

    async def index(
        self,
        request: Request,
        per_page: int = 20,
        page: int = 1,
        archived: bool = False,
        q: str | None = None,
        category_id: int | None = None,
        vendor_id: int | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        active: str | None = None,
        sort: str = "newest",
    ) -> AdminProductPage:
        """List products (admin) — hidden ones included, each row carrying price/thumb/stock and
        `is_visible`. Filterable by ``q`` (name), ``category_id`` and ``active`` (published yes/no),
        sortable by ``sort``. ``archived=true`` lists the soft-deleted (recoverable) rows instead."""
        if archived:
            result = (
                await Product.only_trashed().order_by("id").paginate(per_page, page)
            )
            extras = await _list_extras([p.id for p in result.items()])
            return _page(result, is_visible=False, extras=extras)

        query = Product.with_visibility()
        if q:
            query = query.where_json_like(
                "translations", f"{active_locale()}->name", f"%{q}%"
            )
        if category_id is not None:
            query = query.where("category_id", category_id)
        if vendor_id is not None:
            query = query.where("vendor_id", vendor_id)
        if price_min is not None:
            query = query.where("price_cents", ">=", price_min)
        if price_max is not None:
            query = query.where("price_cents", "<=", price_max)
        if active == "active":
            query = query.where("published", True)
        elif active == "inactive":
            query = query.where("published", False)
        column, direction = _SORTS.get(sort, _SORTS["newest"])
        result = await query.order_by(column, direction).paginate(per_page, page)
        extras = await _list_extras([p.id for p in result.items()])
        return _page(result, extras=extras)

    async def show(self, request: Request, product: Product) -> AdminProductDetailOut:
        """One product with variants + gallery — the editor's read (hidden products included).
        ``product`` is bound via the plain (non-visibility) query, so it's re-fetched through
        ``with_visibility()`` here to get the computed `is_visible` flag for the response."""
        from app.controllers.catalog_controller import gallery_image_out
        from app.models.product_variant import ProductVariant

        product = (
            await Product.with_visibility().where("id", product.id).first_or_fail()
        )
        variants = (
            await ProductVariant.where("product_id", product.id).order_by("id").get()
        )
        from app.models.product import IMAGES

        gallery = [gallery_image_out(m) for m in await product.get_media(IMAGES)]
        return AdminProductDetailOut(
            id=product.id,
            slug=product.slug,
            translations=product.translations,
            status=ProductStatus(product.status).value,
            published=bool(product.published),
            featured=bool(getattr(product, "featured", False)),
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

    async def store(self, request: Request, data: ProductIn) -> AdminProductOut:
        """Create a product (admins only) with per-locale content (en required)."""
        user = _current_user()
        validator = Validator(
            {"category_id": data.category_id, "price_cents": data.price_cents},
            {
                "category_id": "required|integer",
                "price_cents": "required|integer|min:0",
            },
        )
        if validator.fails():
            raise ValidationException(validator.errors())
        translations = validated_translations(data.translations)
        if translations is None:  # ProductIn.translations is required
            abort(500, "Product translations missing after validation.")
        slug = Str.slug(translations["en"]["name"] or "")
        if await Product.with_trashed().where("slug", slug).first() is not None:
            raise ValidationException(
                {
                    "slug": [
                        "This slug is taken (possibly by an archived product — restore it instead)."
                    ]
                }
            )
        product = await Product.create(
            category_id=data.category_id,
            translations=translations,
            slug=slug,
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
        return _admin_product_out(
            product, is_visible=False
        )  # a new draft is never visible

    async def update(
        self, request: Request, product: Product, data: UpdateProductIn
    ) -> AdminProductOut:
        """Update a product — per-locale content, price, category, status, visibility.
        ``authorize_resource`` below already 404'd a non-admin before this body runs (deny-as-404,
        same policy as destroy)."""
        user = _current_user()
        translations = validated_translations(data.translations)
        if translations is not None:
            product.translations = translations
        if data.category_id is not None:
            await Category.find_or_fail(data.category_id)  # 404 on a bogus category
            product.category_id = data.category_id
        if data.price_cents is not None:
            if data.price_cents < 0:
                raise ValidationException(
                    {"price_cents": [trans("shop.errors.price_negative")]}
                )
            product.price_cents = data.price_cents
        if data.status is not None:
            product.status = ProductStatus(data.status)
        if data.published is not None:
            product.published = data.published
        if data.featured is not None:
            product.featured = data.featured
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
        refreshed = (
            await Product.with_visibility().where("id", product.id).first_or_fail()
        )
        return _admin_product_out(
            refreshed, is_visible=bool(getattr(refreshed, "is_visible", False))
        )

    async def destroy(self, request: Request, product: Product) -> MessageOut:
        """ARCHIVE a product (soft delete — order history intact, restorable;
        ``authorize_resource`` below already 404'd a non-admin before this body runs)."""
        user = _current_user()
        await (
            activity()
            .caused_by(user)
            .performed_on(product)
            .with_properties({"slug": product.slug})
            .log("deleted product")
        )
        await product.delete()
        return MessageOut(message="Deleted.")


# store→create (403), update/delete→update/delete (404, deny_as_not_found) — see ProductPolicy.
# Wraps every resource action, including `update` (DR-0057 removed the reason it used to be
# pulled out of this wiring).
AdminProductController.authorize_resource(Product)


async def restore(request: Request) -> AdminProductOut:
    """Bring an archived product back — visibility flags are untouched, so a hidden product
    restores as hidden. Not a CRUD resource action (it targets a soft-deleted row `api_resource`'s
    binding would 404 on), so it stays an explicit route with its own in-handler check."""
    user = _current_user()
    product = (
        await Product.only_trashed().where("id", int(request.path_param("id"))).first()
    )
    if product is None:
        abort(404, trans("shop.errors.product_not_found"))
    if not await user.can("update", product):
        abort(404, trans("shop.errors.product_not_found"))
    await product.restore()
    from app.services.catalog_visibility_service import CatalogVisibilityService

    await CatalogVisibilityService.mark_dirty()
    await (
        activity()
        .caused_by(user)
        .performed_on(product)
        .with_properties({"slug": product.slug})
        .log("restored product")
    )
    refreshed = await Product.with_visibility().where("id", product.id).first_or_fail()
    return _admin_product_out(
        refreshed, is_visible=bool(getattr(refreshed, "is_visible", False))
    )
