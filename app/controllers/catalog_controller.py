"""Catalog read API — categories + product browsing (search, filter, pagination).

Exercises arvel's ORM (query builder, eager-loading, enum casts) + pagination. Models are mapped to
typed response schemas (app.schemas), so the API is strict-typed and its OpenAPI request/response
schemas are generated.
"""

from typing import Any

from arvel import config
from arvel.http import Request
from arvel.localization import current_locale
from arvel.media import Media

from app.enums import ProductStatus
from app.models.category import Category
from app.models.product import IMAGES, Product
from app.schemas import (
    CategoryOut,
    GalleryImageOut,
    ProductOut,
    ProductPage,
    VariantOut,
)


def _in_locale(query: Any) -> Any:
    """Constrained eager-load callback — project the relation in the active locale (its `translation`)."""
    return query.in_locale()


async def _apply_search(query: Any, q: str) -> Any:
    """Full-text `q` search. With a real engine (Meilisearch) go through `Product.search` (Scout) and
    constrain the query to the hit ids — which the visibility scope already intersects with the
    retrievable set. Otherwise (the in-process array engine / tests) fall back to a locale-aware SQL
    match on `translations->'<loc>'->>'name'`, which needs no separately-populated index."""
    if config("search.driver", "array") == "meilisearch":
        hits = await Product.search(q)
        return query.where_in(
            "id", [h.id for h in hits] or [0]
        )  # empty hits → match nothing
    return query.where_json_like(
        "translations", f"{current_locale.get()}->name", f"%{q}%"
    )


def variant_out(v: Product) -> VariantOut:
    return VariantOut(
        id=v.id,
        sku=v.sku,
        name=v.name,
        price_adjustment_cents=v.price_adjustment_cents,
        stock=v.stock,
    )


def category_out(c: Category) -> CategoryOut:
    return CategoryOut(id=c.id, slug=c.slug, translation=c.translation)


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
    category = p.relation(
        "category"
    )  # eager-loaded with in_locale → carries .translation
    variants = p.relation("variants")
    images = await p.get_media(
        IMAGES
    )  # uses the eager-loaded `media` relation when present
    return ProductOut(
        id=p.id,
        slug=p.slug,
        translation=p.translation,
        price_cents=p.price_cents,
        currency=p.currency,
        status=ProductStatus(p.status).value,
        category=category_out(category) if category is not None else None,
        variants=[variant_out(v) for v in variants] if variants is not None else None,
        gallery=[gallery_image_out(m) for m in images],
    )


async def categories_index(request: Request) -> list[CategoryOut]:
    """List **retrievable** categories — published, fully-published ancestor chain, and at least one
    viewable product in the subtree (the retrievable_categories materialized view)."""
    rows = (
        await Category.with_visibility(only_visible=True)
        .in_locale()
        .order_by("slug")
        .get()
    )
    return [category_out(c) for c in rows]


async def products_index(
    request: Request,
    q: str | None = None,
    category: int | None = None,
    per_page: int = 15,
    page: int = 1,
) -> ProductPage:
    """List **retrievable** products (the storefront view): published, with a published vendor, under a
    fully-published category. Typed query params (documented in OpenAPI): `q` (name search),
    `category` (id), `per_page`, `page`."""
    # scopes: only-visible (EXISTS filter), in_locale (project the active locale's `translation`); the
    # eager-loaded category is also locale-projected so its translation comes along.
    query = (
        Product.with_("variants", "media", category=_in_locale)
        .with_visibility(only_visible=True)
        .in_locale()
    )
    if q:
        query = await _apply_search(query, q)
    if category:
        query = query.where("category_id", category)

    result = await query.order_by("slug").paginate(per_page, page)
    return ProductPage(
        data=[await product_out(p) for p in result.items()],
        current_page=result.current_page(),
        last_page=result.last_page(),
        per_page=result.per_page(),
        total=result.total(),
    )


async def products_show(request: Request) -> ProductOut:
    """Show one **retrievable** product by slug (a non-retrievable product 404s — it isn't public)."""
    slug = request.path_param("slug")
    # first_or_fail raises ModelNotFound → the kernel renders it 404 (a non-retrievable product 404s)
    product = (
        await Product.with_("variants", "media", category=_in_locale)
        .where("slug", slug)
        .with_visibility(only_visible=True)
        .in_locale()
        .first_or_fail()
    )
    return await product_out(product)
