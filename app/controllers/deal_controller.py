"""Public deals API — the storefront's "Deals of the Day": every LIVE deal with its product card,
the discounted price, the countdown target, and sell-through stats (available = Σ variant stock,
sold = Σ order-line quantity on paid/shipped/delivered orders)."""

from arvel import DB
from arvel.http import Request

from app.controllers.catalog_controller import _in_locale, product_out
from app.controllers.serializers import iso as _iso
from app.models.deal import Deal
from app.models.product import Product
from app.schemas import DealOut
from app.services import deal_service


async def _sold_counts(product_ids: list[int]) -> dict[int, int]:
    """One aggregate query: units sold per product on orders that actually completed."""
    if not product_ids:
        return {}
    placeholders = ", ".join(str(int(pid)) for pid in product_ids)
    rows = await DB.select(
        "SELECT pv.product_id AS product_id, COALESCE(SUM(oi.quantity), 0) AS sold "
        "FROM order_items oi "
        "JOIN product_variants pv ON pv.id = oi.product_variant_id "
        "JOIN orders o ON o.id = oi.order_id "
        f"WHERE o.status IN ('paid', 'shipped', 'delivered') AND pv.product_id IN ({placeholders}) "
        "GROUP BY pv.product_id"
    )
    return {int(r["product_id"]): int(r["sold"]) for r in rows}


async def index(request: Request) -> list[DealOut]:
    deals = await Deal.order_by("ends_at").get()
    live = [d for d in deals if deal_service.is_live(d)]
    if not live:
        return []
    product_ids = [d.product_id for d in live]
    products = {
        p.id: p
        for p in await Product.with_("variants", "media", category=_in_locale)
        .with_visibility(only_visible=True)
        .in_locale()
        .where_in("id", product_ids)
        .get()
    }
    sold = await _sold_counts(list(products.keys()))
    out: list[DealOut] = []
    for deal in live:
        product = products.get(deal.product_id)
        if product is None:
            continue  # the product left the storefront; its deal goes with it
        variants = product.relation("variants") or []
        out.append(
            DealOut(
                id=deal.id,
                percent_off=deal.percent_off,
                deal_price_cents=deal_service.deal_price_cents(
                    product.price_cents, deal
                ),
                ends_at=_iso(deal.ends_at) or "",
                available=sum(v.stock for v in variants),
                sold=sold.get(product.id, 0),
                product=await product_out(product, deal),
            )
        )
    return out
