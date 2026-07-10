"""Catalog read API — categories + product browsing (search, filter, pagination)."""

from typing import Any

from arvel import config
from arvel.http import Request
from arvel.media import Media

from app.enums import ProductStatus
from app.controllers.serializers import iso as _iso
from app.i18n import active_locale
from app.models.category import Category
from app.models.product import IMAGES, Product
from app.schemas import (
    CategoryOut,
    GalleryImageOut,
    ProductDealOut,
    ProductFeed,
    ProductOut,
    ProductPage,
    VariantOut,
)
from app.services import deal_service


def in_locale_relation(query: Any) -> Any:
    """Constrained eager-load callback — project the relation in the active locale (its `translation`)."""
    return query.in_locale()


_in_locale = in_locale_relation


async def _apply_search(query: Any, q: str) -> Any:
    """Full-text `q` search. With a real engine (Meilisearch) go through `Product.search` (Scout) and
    constrain the query to the hit ids — which the visibility scope already intersects with the
    retrievable set. Otherwise (the in-process array engine / tests) fall back to a locale-aware SQL
    match on `translations->'<loc>'->>'name'`, which needs no separately-populated index."""
    if config("search.driver", "array") == "meilisearch":
        hits = await Product.search(
            q
        ).get()  # search() returns a SearchBuilder; .get() runs it
        return query.where_in(
            "id", [h.id for h in hits] or [0]
        )  # empty hits → match nothing
    return query.where_json_like("translations", f"{active_locale()}->name", f"%{q}%")


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
    """A media-library item → its serving URLs (original + thumb/preview conversions).

    Product images are public: ``get_url`` returns a public bucket/CDN URL when the disk has one
    configured (config/filesystems → s3 ``url``); the ``local`` disk has no url base, so we fall
    back to the app-streamed ``/api/media`` route."""
    mid = media.id

    def _url(conversion: str | None) -> str:
        url = media.get_url(conversion)
        if url and url.startswith(("http://", "https://")):
            return url  # public bucket / CDN URL
        return f"/api/media/{mid}" + (
            f"/{conversion}" if conversion else ""
        )  # local-disk fallback

    return GalleryImageOut(
        id=mid, url=_url(None), thumb_url=_url("thumb"), preview_url=_url("preview")
    )


def deal_out(p: Product, deal: Any | None) -> ProductDealOut | None:
    if deal is None:
        return None
    return ProductDealOut(
        id=deal.id,
        percent_off=deal.percent_off,
        deal_price_cents=deal_service.deal_price_cents(p.price_cents, deal),
        ends_at=_iso(deal.ends_at) or "",
    )


async def product_out(p: Product, deal: Any | None = None) -> ProductOut:
    category = p.relation(
        "category"
    )  # eager-loaded with in_locale → carries .translation
    variants = p.relation("product_variants")
    images = await p.get_media(
        IMAGES
    )  # uses the eager-loaded `media` relation when present
    rating_count = int(getattr(p, "rating_count", 0) or 0)
    rating_sum = int(getattr(p, "rating_sum", 0) or 0)
    return ProductOut(
        id=p.id,
        slug=p.slug,
        translation=p.translation,
        rating_avg=round(rating_sum / rating_count, 1) if rating_count else None,
        rating_count=rating_count,
        price_cents=p.price_cents,
        currency=p.currency,
        status=ProductStatus(p.status).value,
        featured=bool(getattr(p, "featured", False)),
        created_at=_iso(getattr(p, "created_at", None)),
        deal=deal_out(p, deal),
        category=category_out(category) if category is not None else None,
        variants=[variant_out(v) for v in variants] if variants is not None else None,
        gallery=[gallery_image_out(m) for m in images],
    )


async def _category_tile_images(categories: list[Any]) -> dict[int, str]:
    """One representative product thumb per category (subtree roll-up) for the category tiles.
    Two queries total: the retrievable product→category map, then media for the chosen products."""
    # the retrievable set via the same visibility scope the storefront uses (EXISTS against the view)
    retrievable = await Product.with_visibility(only_visible=True).order_by("id").get()
    children: dict[int | None, list[int]] = {}
    all_cats = await Category.all()
    for c in all_cats:
        children.setdefault(c.parent_id, []).append(c.id)

    direct: dict[int, int] = {}
    for p in retrievable:
        direct.setdefault(int(p.category_id), int(p.id))

    def subtree_first(cat_id: int) -> int | None:
        stack = [cat_id]
        while stack:
            cid = stack.pop(0)
            if cid in direct:
                return direct[cid]
            stack.extend(children.get(cid, []))
        return None

    chosen = {c.id: pid for c in categories if (pid := subtree_first(c.id)) is not None}
    if not chosen:
        return {}
    products = (
        await Product.with_("media").where_in("id", list(set(chosen.values()))).get()
    )
    thumbs: dict[int, str] = {}
    for product in products:
        images = await product.get_media(IMAGES)
        if images:
            thumbs[product.id] = gallery_image_out(images[0]).thumb_url
    return {cat_id: thumbs[pid] for cat_id, pid in chosen.items() if pid in thumbs}


async def categories_index(request: Request) -> list[CategoryOut]:
    """List **retrievable** categories — published, fully-published ancestor chain, and at least one
    viewable product in the subtree (the retrievable_categories materialized view). Each carries a
    derived ``image_url`` (a subtree product's thumb) for the storefront's category tiles."""
    rows = (
        await Category.with_visibility(only_visible=True)
        .in_locale()
        .order_by("slug")
        .get()
    )
    images = await _category_tile_images(rows)
    return [
        CategoryOut(
            id=c.id, slug=c.slug, translation=c.translation, image_url=images.get(c.id)
        )
        for c in rows
    ]


_SORTS: dict[str, tuple[str, str]] = {
    "featured": ("slug", "asc"),
    "price_asc": ("price_cents", "asc"),
    "price_desc": ("price_cents", "desc"),
    "newest": ("id", "desc"),
    "name": ("slug", "asc"),
}


async def _category_subtree_ids(slug: str) -> list[int]:
    """The category with ``slug`` plus all its descendants — so browsing a parent (e.g. Audio) shows
    products in its child categories (Headphones/Earbuds/…), not just ones filed directly on it."""
    root = await Category.where("slug", slug).first()
    if root is None:
        return []
    cats = await Category.all()
    children: dict[int, list[int]] = {}
    for c in cats:
        if c.parent_id is not None:
            children.setdefault(c.parent_id, []).append(c.id)
    ids: list[int] = []
    stack: list[int] = [root.id]
    while stack:
        cid = stack.pop()
        ids.append(cid)
        stack.extend(children.get(cid, []))
    return ids


async def _visible_products_query(
    q: str | None,
    category: str | None,
    featured: bool | None,
    min_price: int | None,
    max_price: int | None,
) -> Any:
    """The retrievable-storefront product query with the common filters applied (no ordering yet).
    Shared by the offset listing and the cursor feed so both see the exact same visibility rules.
    Scopes: only-visible (EXISTS filter), in_locale (project the active locale's `translation`); the
    eager-loaded category is also locale-projected so its translation comes along."""
    query = (
        Product.with_("product_variants", "media", category=_in_locale)
        .with_visibility(only_visible=True)
        .in_locale()
    )
    if q:
        query = await _apply_search(query, q)
    if category:
        query = query.where_in(
            "category_id", await _category_subtree_ids(category) or [0]
        )
    if featured:
        query = query.where("featured", True)
    if min_price is not None:
        query = query.where("price_cents", ">=", min_price)
    if max_price is not None:
        query = query.where("price_cents", "<=", max_price)
    return query


async def _product_outs(result: Any) -> list[ProductOut]:
    deals = await deal_service.active_deals_for([p.id for p in result.items()])
    return [await product_out(p, deals.get(p.id)) for p in result.items()]


async def products_index(
    request: Request,
    q: str | None = None,
    category: str | None = None,
    sort: str = "featured",
    featured: bool | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    per_page: int = 15,
    page: int = 1,
) -> ProductPage:
    """List **retrievable** products (the storefront view): published, with a published vendor, under a
    fully-published category. Query params (documented in OpenAPI): `q` (name search), `category`
    (slug — includes descendant categories), `sort` (featured|price_asc|price_desc|newest|name),
    `per_page`, `page`."""
    query = await _visible_products_query(q, category, featured, min_price, max_price)
    column, direction = _SORTS.get(sort, _SORTS["featured"])
    result = await query.order_by(column, direction).paginate(per_page, page)
    return ProductPage(
        data=await _product_outs(result),
        current_page=result.current_page(),
        last_page=result.last_page(),
        per_page=result.per_page(),
        total=result.total(),
    )


async def products_feed(
    request: Request,
    q: str | None = None,
    category: str | None = None,
    sort: str = "featured",
    featured: bool | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    per_page: int = 15,
    cursor: str | None = None,
) -> ProductFeed:
    """Infinite-scroll product feed — keyset (cursor) pagination. Unlike the offset listing, pages
    stay correct even when products are published mid-scroll (no page drift / duplicate rows). Pass
    the previous response's `next_cursor` back as `cursor` to fetch the next page; a null
    `next_cursor` means the end of the feed. Same filters/sorts as the offset listing."""
    query = await _visible_products_query(q, category, featured, min_price, max_price)
    column, direction = _SORTS.get(sort, _SORTS["featured"])
    result = await query.order_by(column, direction).cursor_paginate(per_page, cursor)
    return ProductFeed(
        data=await _product_outs(result),
        per_page=result.per_page(),
        next_cursor=result.next_cursor(),
        prev_cursor=result.previous_cursor(),
    )


async def products_show(request: Request) -> ProductOut:
    """Show one **retrievable** product by slug (a non-retrievable product 404s — it isn't public)."""
    slug = request.path_param("slug")
    # first_or_fail raises ModelNotFound → the kernel renders it 404 (a non-retrievable product 404s)
    product = (
        await Product.with_("product_variants", "media", category=_in_locale)
        .where("slug", slug)
        .with_visibility(only_visible=True)
        .in_locale()
        .first_or_fail()
    )
    return await product_out(product, await deal_service.active_deal(product.id))
