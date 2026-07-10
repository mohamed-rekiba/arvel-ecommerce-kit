"""The TaxRate model — one tax rate per shipping-address country (basis points; 700 = 7.00%).
A country with no row here falls to `tax_service.DEFAULT_TAX_RATE_BPS` — see DR-0063."""

from typing import ClassVar

from arvel import Model


class TaxRate(Model):
    __table_name__ = "tax_rates"
    __fields__: ClassVar[dict[str, type]] = {
        "country": str,
        "rate_bps": int,
    }
    __fillable__: ClassVar[list[str]] = ["country", "rate_bps"]
    # no __casts__ — both are native scalar columns (DR-0063)
