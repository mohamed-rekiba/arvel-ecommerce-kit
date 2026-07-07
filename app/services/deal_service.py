"""Deal domain rules — ONE place for "is this deal live" and the discounted-price math, shared by
the storefront payloads (display), the cart (price snapshot at add time), and checkout (the
authoritative re-price inside the order transaction). Current-price-wins: an expired deal never
leaks into an order, a deal that started after the item was carted is honored."""

from decimal import Decimal

from arvel.dates import Date
from arvel.support import Money

from app.enums import Currency
from app.models.deal import Deal


def is_live(deal: Deal, now: Date | None = None) -> bool:
    moment = now or Date.now()
    if not deal.active:
        return False
    if deal.starts_at is not None and moment < deal.starts_at:
        return False
    return not (deal.ends_at is not None and moment > deal.ends_at)


async def active_deal(product_id: int) -> Deal | None:
    """The live deal for one product (window + active). Newest wins if several overlap."""
    deals = await Deal.where("product_id", product_id).order_by("id", "desc").get()
    for deal in deals:
        if is_live(deal):
            return deal
    return None


async def active_deals_for(product_ids: list[int]) -> dict[int, Deal]:
    """Batch lookup for listings — one query, newest live deal per product."""
    if not product_ids:
        return {}
    deals = await Deal.where_in("product_id", product_ids).order_by("id", "desc").get()
    live: dict[int, Deal] = {}
    for deal in deals:
        if deal.product_id not in live and is_live(deal):
            live[deal.product_id] = deal
    return live


def deal_price_cents(base_cents: int, deal: Deal) -> int:
    """The discounted unit price: percent off the FULL unit price (base + variant adjustment).
    Money.times rounds the minor units half-up (vs the old floor), so the discount is currency-correct."""
    keep = Decimal(100 - deal.percent_off) / Decimal(100)
    return Money(base_cents, Currency.USD.value).times(keep).amount


async def current_unit_price_cents(
    product_id: int, base_cents: int, deal: Deal | None = None
) -> int:
    """The price to charge RIGHT NOW for one unit — base price with the live deal applied."""
    live = deal if deal is not None and is_live(deal) else await active_deal(product_id)
    return deal_price_cents(base_cents, live) if live else base_cents
