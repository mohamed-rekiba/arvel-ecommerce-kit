"""Admin category + vendor management. Categories carry per-locale names and nest; vendors gate
every product they own via ``published``. catalog.* permission surface; every mutation is
activity-logged; visibility changes flag the retrievable views dirty (debounced refresh).

Neither Category nor Vendor has a registered Gate policy — their authorization is a flat
catalog.* permission check with no per-object dimension, so (K5/DR-0056) they convert to
``api_resource`` + a declared ``Authorize`` per action rather than ``authorize_resource``: inventing
a policy just to reach the pipeline would either duplicate this same permission check under another
name or force a 403→404 contract flip these resources never asked for.
"""

from arvel import abort
from app.i18n import trans
from arvel.activitylog import activity
from arvel.auth.middleware import Authorize
from arvel.http import Request
from arvel.routing import Controller, ControllerMiddleware
from arvel.support import Str, current_user
from arvel.validation import ValidationException

from app.controllers.admin_product_controller import validated_translations
from app.enums import Permission
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas import (
    AdminCategoryOut,
    AdminCategoryPage,
    AdminVendorOut,
    CategoryIn,
    CategoryUpdateIn,
    MessageOut,
    VendorIn,
    VendorUpdateIn,
)
from app.services.catalog_visibility_service import CatalogVisibilityService


def _current_user() -> User:
    user: User | None = current_user.get()
    if user is None:
        abort(401, trans("shop.errors.unauthenticated"))
    return user


def _category_out(category: Category, *, is_visible: bool = False) -> AdminCategoryOut:
    return AdminCategoryOut(
        id=category.id,
        slug=category.slug,
        translations=category.translations,
        parent_id=category.parent_id,
        published=bool(category.published),
        is_visible=is_visible,
    )


def _vendor_out(vendor: Vendor) -> AdminVendorOut:
    return AdminVendorOut(
        id=vendor.id,
        name=vendor.name,
        slug=vendor.slug,
        published=bool(vendor.published),
    )


async def _slug_taken(
    model: type[Category] | type[Vendor], slug: str, *, ignore_id: int | None = None
) -> bool:
    existing = await model.where("slug", slug).first()
    return existing is not None and existing.id != ignore_id


# --- categories ---


class CategoryController(Controller):
    """Category CRUD, consolidated (K5) from the old split between this module and
    ``admin_product_controller.categories_index``: one resource, one controller. ``update``
    registers through this class's normal ``Router.resource()`` wiring — it used to be pulled out
    into an explicit route because arvel's resource generator bound it to both PUT and PATCH under
    one route name, tripping Litestar's one-operationId-per-operation OpenAPI check; that's fixed
    at the framework level now (DR-0057), so its ``Authorize`` middleware is declared here like
    every other action."""

    @classmethod
    def middleware(cls) -> list[ControllerMiddleware]:
        return [
            ControllerMiddleware(
                Authorize(Permission.CATALOG_VIEW.value), only=("index",)
            ),
            ControllerMiddleware(
                Authorize(Permission.CATALOG_CREATE.value), only=("store",)
            ),
            ControllerMiddleware(
                Authorize(Permission.CATALOG_UPDATE.value), only=("update",)
            ),
            ControllerMiddleware(
                Authorize(Permission.CATALOG_DELETE.value), only=("destroy",)
            ),
        ]

    async def index(
        self, request: Request, per_page: int = 50, page: int = 1
    ) -> AdminCategoryPage:
        """List **all** categories (admin) with `is_visible` (inline EXISTS column)."""
        result = (
            await Category.with_visibility().order_by("id").paginate(per_page, page)
        )
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

    async def store(self, request: Request, data: CategoryIn) -> AdminCategoryOut:
        user = _current_user()
        translations = validated_translations(data.translations)
        if translations is None:
            abort(500, "Category translations missing after validation.")
        slug = Str.slug(translations["en"]["name"] or "")
        if await _slug_taken(Category, slug):
            raise ValidationException(
                {"slug": [trans("shop.errors.category_slug_exists")]}
            )
        if data.parent_id is not None:
            await Category.find_or_fail(data.parent_id)
        category = await Category.create(
            translations=translations,
            slug=slug,
            parent_id=data.parent_id,
            published=data.published,
        )
        await CatalogVisibilityService.mark_dirty()
        await (
            activity()
            .caused_by(user)
            .performed_on(category)
            .with_properties({"slug": slug})
            .log("created category")
        )
        return _category_out(category)

    async def update(
        self, request: Request, category: Category, data: CategoryUpdateIn
    ) -> AdminCategoryOut:
        # catalog.update is enforced by this controller's Authorize middleware (DR-0055) — it
        # runs before binding, so a denied caller 403s uniformly whether or not the id exists.
        user = _current_user()
        translations = validated_translations(data.translations)
        if translations is not None:
            category.translations = translations
        if data.parent_id is not None:
            if data.parent_id == category.id:
                raise ValidationException(
                    {"parent_id": [trans("shop.errors.category_self_parent")]}
                )
            await Category.find_or_fail(data.parent_id)
            category.parent_id = data.parent_id
        if data.published is not None:
            category.published = data.published
        await category.save()
        await CatalogVisibilityService.mark_dirty()
        await (
            activity()
            .caused_by(user)
            .performed_on(category)
            .with_properties(
                {
                    "changed": [
                        k
                        for k in ("translations", "parent_id", "published")
                        if getattr(data, k) is not None
                    ]
                }
            )
            .log("updated category")
        )
        return _category_out(category)

    async def destroy(self, request: Request, category: Category) -> MessageOut:
        # catalog.delete is enforced by the controller's Authorize middleware (DR-0055/K5).
        user = _current_user()
        if await Product.where("category_id", category.id).first() is not None:
            raise ValidationException(
                {"category": [trans("shop.errors.category_has_products")]}
            )
        if await Category.where("parent_id", category.id).first() is not None:
            raise ValidationException(
                {"category": [trans("shop.errors.category_has_children")]}
            )
        await (
            activity()
            .caused_by(user)
            .performed_on(category)
            .with_properties({"slug": category.slug})
            .log("deleted category")
        )
        await category.delete()
        await CatalogVisibilityService.mark_dirty()
        return MessageOut(message="Category deleted.")


# --- vendors ---


class VendorController(Controller):
    """Vendor CRUD — index/store/update only. There's no `destroy`: a vendor with products still
    attached can't be safely removed, so admins retire one via `published=False` instead (same
    pattern as a category with children). ``update`` registers through this class's normal
    ``Router.resource()`` wiring — see ``CategoryController``'s docstring for why it no longer
    needs to be pulled out."""

    @classmethod
    def middleware(cls) -> list[ControllerMiddleware]:
        return [
            ControllerMiddleware(
                Authorize(Permission.CATALOG_VIEW.value), only=("index",)
            ),
            ControllerMiddleware(
                Authorize(Permission.CATALOG_CREATE.value), only=("store",)
            ),
            ControllerMiddleware(
                Authorize(Permission.CATALOG_UPDATE.value), only=("update",)
            ),
        ]

    async def index(self, request: Request) -> list[AdminVendorOut]:
        vendors = await Vendor.order_by("id").get()
        return [_vendor_out(v) for v in vendors]

    async def store(self, request: Request, data: VendorIn) -> AdminVendorOut:
        user = _current_user()
        if not data.name.strip():
            raise ValidationException(
                {"name": [trans("shop.errors.vendor_name_required")]}
            )
        slug = Str.slug(data.name)
        if await _slug_taken(Vendor, slug):
            raise ValidationException(
                {"slug": [trans("shop.errors.vendor_slug_exists")]}
            )
        vendor = await Vendor.create(
            name=data.name, slug=slug, published=data.published
        )
        await CatalogVisibilityService.mark_dirty()
        await (
            activity()
            .caused_by(user)
            .performed_on(vendor)
            .with_properties({"slug": slug})
            .log("created vendor")
        )
        return _vendor_out(vendor)

    async def update(
        self, request: Request, vendor: Vendor, data: VendorUpdateIn
    ) -> AdminVendorOut:
        """Rename or (un)publish a vendor — the publish flag gates the retrievability of every
        product the vendor owns (recomputed by the debounced views refresh). catalog.update is
        enforced by this controller's Authorize middleware (DR-0055)."""
        user = _current_user()
        if data.name is not None:
            if not data.name.strip():
                raise ValidationException(
                    {"name": [trans("shop.errors.vendor_name_empty")]}
                )
            vendor.name = data.name
        if data.published is not None:
            vendor.published = data.published
        await vendor.save()
        await CatalogVisibilityService.mark_dirty()
        await (
            activity()
            .caused_by(user)
            .performed_on(vendor)
            .with_properties(
                {
                    "changed": [
                        k for k in ("name", "published") if getattr(data, k) is not None
                    ]
                }
            )
            .log("updated vendor")
        )
        return _vendor_out(vendor)
