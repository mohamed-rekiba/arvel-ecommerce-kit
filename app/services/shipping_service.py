"""Shipping-rate resolution — one place for "what does this method cost", shared by checkout
(the only caller today). The client sends a method CODE only; the rate is always read from the
`shipping_methods` table, never from the request (DR-0064)."""

from app.models.shipping_method import ShippingMethod
from arvel.validation import ValidationException

DEFAULT_SHIPPING_METHOD = "standard"  # CheckoutIn default; = today's flat 500c behavior


async def resolve_rate_cents(code: str) -> int:
    """The shipping rate (integer cents) for a selected method CODE. Unknown or inactive code ->
    422 (an unavailable method the customer explicitly picked is a client error, not a silent
    fallback — the deliberate contrast with tax_service's unlisted-country default)."""
    row = await ShippingMethod.where("code", code).where("active", True).first()
    if row is None:
        raise ValidationException(
            {"shipping_method": [f"'{code}' is not an available shipping method."]}
        )
    return row.rate_cents


async def list_methods() -> list[ShippingMethod]:
    """Active methods for the storefront selector, cheapest/sorted first."""
    rows = (
        await ShippingMethod.where("active", True)
        .order_by("sort")
        .order_by("rate_cents")
        .get()
    )
    return list(rows)
