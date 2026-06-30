"""Catalog read API — categories + product browsing (search, filter, pagination).

Exercises arvel's ORM (query builder, eager-loading, enum casts), pagination (LengthAwarePaginator
→ Laravel JSON shape), and request query handling. Returns paginator/model objects directly — the
arvel kernel serializes them to Laravel's JSON shape (incl. the Date type-encoder for timestamps).
"""

from typing import Any

from arvel import abort

from app.enums import ProductStatus
from app.models.category import Category
from app.models.product import Product


async def categories_index(request) -> Any:
    """GET /api/categories — all categories (flat)."""
    return await Category.order_by("name").get()


async def products_index(request) -> Any:
    """GET /api/products — active products, with optional ?q= search, ?category= and ?status=
    filters, paginated (?page=, ?per_page=)."""
    q = request.query("q")
    category_id = request.query("category")
    status = request.query("status")
    per_page = int(request.query("per_page", 15))

    query = (
        Product.query()
        .with_("category", "variants")
        .when(q, lambda b, term: b.where("name", "like", f"%{term}%"))
        .when(category_id, lambda b, cid: b.where("category_id", cid))
        # default to ACTIVE products unless an explicit status filter is given
        .when(
            status,
            lambda b, s: b.where("status", ProductStatus(s).value),
            lambda b: b.where("status", ProductStatus.ACTIVE.value),
        )
        .order_by("name")
    )
    return await query.paginate(per_page)


async def products_show(request) -> Any:
    """GET /api/products/{slug} — one product with its category + variants eager-loaded."""
    slug = request.path_param("slug")
    product = await Product.with_("category", "variants").where("slug", slug).first()
    if product is None:
        abort(404, "Product not found")
    return product
