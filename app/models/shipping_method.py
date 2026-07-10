"""The ShippingMethod model — one flat, integer-cents rate per selectable shipping method
(standard/express). A method with no row, or `active=False`, is not available at checkout —
see `shipping_service.resolve_rate_cents` and DR-0064."""

from typing import ClassVar

from arvel import Model


class ShippingMethod(Model):
    __table_name__ = "shipping_methods"
    __fields__: ClassVar[dict[str, type]] = {
        "code": str,
        "name": str,
        "rate_cents": int,
        "active": bool,
        "sort": int,
    }
    __fillable__: ClassVar[list[str]] = ["code", "name", "rate_cents", "active", "sort"]
    # no __casts__ — all native scalar columns (same rationale as TaxRate, DR-0064)
