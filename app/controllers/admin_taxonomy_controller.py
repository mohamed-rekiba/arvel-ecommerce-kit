"""Admin category + vendor management. Categories carry per-locale names and nest; vendors gate
every product they own via ``published``. catalog.* permission surface; every mutation is
activity-logged; visibility changes flag the retrievable views dirty (debounced refresh)."""

from arvel import abort
from arvel.activitylog import activity
from arvel.http import Request
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
        abort(401, "Unauthenticated")
    return user


async def _require(user: User, permission: Permission) -> None:
    if not await user.can(permission.value):
        abort(403, "You lack catalog access.")


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


async def category_store(request: Request, data: CategoryIn) -> AdminCategoryOut:
    user = _current_user()
    await _require(user, Permission.CATALOG_CREATE)
    translations = validated_translations(data.translations)
    if translations is None:
        abort(500, "Category translations missing after validation.")
    slug = Str.slug(translations["en"]["name"] or "")
    if await _slug_taken(Category, slug):
        raise ValidationException(
            {"slug": ["A category with this slug already exists."]}
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


async def category_update(
    request: Request, id: Category, data: CategoryUpdateIn
) -> AdminCategoryOut:
    # catalog.update is enforced by the route's Authorize middleware (DR-0055) — it runs before
    # binding, so a denied caller 403s uniformly whether or not the id exists.
    user = _current_user()
    category = id
    translations = validated_translations(data.translations)
    if translations is not None:
        category.translations = translations
    if data.parent_id is not None:
        if data.parent_id == category.id:
            raise ValidationException(
                {"parent_id": ["A category can't parent itself."]}
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


async def category_destroy(request: Request, id: Category) -> MessageOut:
    # catalog.delete is enforced by the route's Authorize middleware (DR-0055).
    user = _current_user()
    category = id
    if await Product.where("category_id", category.id).first() is not None:
        raise ValidationException(
            {"category": ["This category still has products — move them first."]}
        )
    if await Category.where("parent_id", category.id).first() is not None:
        raise ValidationException(
            {"category": ["This category has sub-categories — move them first."]}
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


async def vendors_index(request: Request) -> list[AdminVendorOut]:
    user = _current_user()
    await _require(user, Permission.CATALOG_VIEW)
    vendors = await Vendor.order_by("id").get()
    return [_vendor_out(v) for v in vendors]


async def vendor_store(request: Request, data: VendorIn) -> AdminVendorOut:
    user = _current_user()
    await _require(user, Permission.CATALOG_CREATE)
    if not data.name.strip():
        raise ValidationException({"name": ["The vendor name is required."]})
    slug = Str.slug(data.name)
    if await _slug_taken(Vendor, slug):
        raise ValidationException({"slug": ["A vendor with this slug already exists."]})
    vendor = await Vendor.create(name=data.name, slug=slug, published=data.published)
    await CatalogVisibilityService.mark_dirty()
    await (
        activity()
        .caused_by(user)
        .performed_on(vendor)
        .with_properties({"slug": slug})
        .log("created vendor")
    )
    return _vendor_out(vendor)


async def vendor_update(
    request: Request, id: Vendor, data: VendorUpdateIn
) -> AdminVendorOut:
    """Rename or (un)publish a vendor — the publish flag gates the retrievability of every
    product the vendor owns (recomputed by the debounced views refresh). catalog.update is
    enforced by the route's Authorize middleware (DR-0055)."""
    user = _current_user()
    vendor = id
    if data.name is not None:
        if not data.name.strip():
            raise ValidationException({"name": ["The vendor name can't be empty."]})
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
