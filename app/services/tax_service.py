"""Tax-rate resolution — one place for "what rate applies to this shipping country", shared by
checkout (the only caller today). Country is the jurisdiction key because the address/order model
carries no region/state column (DR-0063)."""

from app.models.tax_rate import TaxRate

DEFAULT_TAX_RATE_BPS = (
    1000  # 10% — equals today's flat rate, so an unlisted country is unchanged
)


async def resolve_rate_bps(country: str) -> int:
    """The tax rate (basis points) for a shipping country. No `tax_rates` row → the documented
    default; never raises — an unlisted jurisdiction is a known, supported case, not an error.
    `country` must be the server-validated `ship_country`, never a client-supplied value."""
    row = await TaxRate.where("country", country).first()
    return row.rate_bps if row is not None else DEFAULT_TAX_RATE_BPS
