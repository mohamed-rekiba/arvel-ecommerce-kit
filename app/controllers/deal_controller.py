"""Public deals API — the storefront's "Deals of the Day": every LIVE deal with its product card,
the discounted price, the countdown target, and sell-through stats (available = Σ variant stock,
sold = Σ order-line quantity on paid/shipped/delivered orders)."""

from typing import Any

from arvel import DB
from arvel.features import Feature
from arvel.http import Request
from arvel.support import current_user

from app.controllers.catalog_controller import in_locale_relation, product_out
from app.controllers.serializers import iso as _iso
from app.enums import OrderStatus
from app.models.deal import Deal
from app.models.product import Product
from app.schemas import DealOut
from app.services import deal_service

_SOLD_STATUSES = [
    OrderStatus.PAID.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
]


async def _sold_counts(product_ids: list[int]) -> dict[int, int]:
    """Units sold per product on orders that actually completed."""
    if not product_ids:
        return {}
    counts = await (
        DB.table("order_items")
        .join(
            "product_variants",
            "product_variants.id",
            "=",
            "order_items.product_variant_id",
        )
        .join("orders", "orders.id", "=", "order_items.order_id")
        .where_in("orders.status", _SOLD_STATUSES)
        .where_in("product_variants.product_id", product_ids)
        .group_by("product_variants.product_id")
        .select_raw(
            "product_variants.product_id AS product_id, "
            "COALESCE(SUM(order_items.quantity), 0) AS sold"
        )
        .pluck("sold", "product_id")
    )
    return {int(pid): int(sold) for pid, sold in counts.items()}


async def index(request: Request) -> list[DealOut]:
    deals = await Deal.order_by("ends_at").get()
    live = [d for d in deals if deal_service.is_live(d)]
    if not live:
        return []
    product_ids = [d.product_id for d in live]
    products = {
        p.id: p
        for p in await Product.with_(
            "product_variants", "media", category=in_locale_relation
        )
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
        variants: list[Any] = list(product.relation("product_variants") or [])
        out.append(
            DealOut(
                id=deal.id,
                percent_off=deal.percent_off,
                deal_price_cents=deal_service.deal_price_cents(
                    product.price_cents, deal
                ),
                ends_at=_iso(deal.ends_at) or "",
                available=sum(int(v.stock) for v in variants),
                sold=sold.get(product.id, 0),
                product=await product_out(product, deal),
            )
        )
    # K14 "promoted-deals": best-discount-first for the enabled segment; otherwise the control
    # order above (soonest-ending-first) is left as-is.
    if await Feature.active("promoted-deals", current_user.get()):
        out.sort(key=lambda d: d.percent_off, reverse=True)
    return out
