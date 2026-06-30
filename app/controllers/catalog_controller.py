"""Catalog read API — categories + product browsing (search, filter, pagination).

Exercises arvel's ORM (query builder, eager-loading, enum casts) + pagination. Models are mapped to
typed response schemas (app.schemas), so the API is strict-typed and its OpenAPI request/response
schemas are generated.
"""

from arvel.http import Request
from arvel.media import Media

from app.enums import ProductStatus
from app.models.category import Category
from app.models.product import IMAGES, Product
from app.schemas import CategoryOut, GalleryImageOut, ProductOut, ProductPage, VariantOut


def variant_out(v: Product) -> VariantOut:
    return VariantOut(
        id=v.id, sku=v.sku, name=v.name,
        price_adjustment_cents=v.price_adjustment_cents, stock=v.stock,
    )


def category_out(c: Category) -> CategoryOut:
    return CategoryOut(id=c.id, name=c.name, slug=c.slug)


def gallery_image_out(media: Media) -> GalleryImageOut:
    """A media-library item → its kit serving URLs (original + thumb/preview conversions)."""
    mid = media.id
    return GalleryImageOut(
        id=mid,
        url=f"/api/media/{mid}",
        thumb_url=f"/api/media/{mid}/thumb",
        preview_url=f"/api/media/{mid}/preview",
    )


async def product_out(p: Product) -> ProductOut:
    category = p.relation("category")
    variants = p.relation("variants")
    images = await p.get_media(IMAGES)  # uses the eager-loaded `media` relation when present
    return ProductOut(
        id=p.id, name=p.name, slug=p.slug, description=p.description,
        price_cents=p.price_cents, currency=p.currency, status=ProductStatus(p.status).value,
        category=category_out(category) if category is not None else None,
        variants=[variant_out(v) for v in variants] if variants is not None else None,
        gallery=[gallery_image_out(m) for m in images],
    )


async def categories_index(request: Request) -> list[CategoryOut]:
    """List all product categories."""
    rows = await Category.order_by("name").get()
    return [category_out(c) for c in rows]


async def products_index(
    request: Request,
    q: str | None = None,
    category: int | None = None,
    status: str | None = None,
    per_page: int = 15,
    page: int = 1,
) -> ProductPage:
    """List active products. Typed query params (documented in OpenAPI): `q` (name search),
    `category` (id), `status`, `per_page`, `page`."""
    query = Product.with_("category", "variants", "media")
    if q:
        query = query.where("name", "like", f"%{q}%")
    if category:
        query = query.where("category_id", category)
    # default to ACTIVE products unless an explicit status filter is given
    chosen = ProductStatus(status).value if status else ProductStatus.ACTIVE.value
    query = query.where("status", chosen).order_by("name")

    result = await query.paginate(per_page, page)
    return ProductPage(
        data=[await product_out(p) for p in result.items()],
        current_page=result.current_page(),
        last_page=result.last_page(),
        per_page=result.per_page(),
        total=result.total(),
    )


async def products_show(request: Request) -> ProductOut:
    """Show one product (by slug) with its category, variants + image gallery eager-loaded."""
    slug = request.path_param("slug")
    # first_or_fail raises ModelNotFound → the kernel renders it 404 (no manual guard)
    product = await Product.with_("category", "variants", "media").where("slug", slug).first_or_fail()
    return await product_out(product)
