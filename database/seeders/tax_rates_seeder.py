"""Seeds the jurisdictions K17 actually lists a rate for. **EG is deliberately omitted** — the
seeded test customer ships to EG (`database_seeder.py`), so their checkout exercises the
no-entry→default path (`tax_service.DEFAULT_TAX_RATE_BPS`) for real, not as a fabricated case."""

from arvel.database import Seeder

from app.models.tax_rate import TaxRate

RATES = {
    "US": 700,
    "CA": 500,
    "GB": 2000,
    "DE": 1900,
    "FR": 2000,
}


class TaxRatesSeeder(Seeder):
    """Idempotent: safe to re-run (each country is first-or-created)."""

    async def run(self) -> None:
        for country, rate_bps in RATES.items():
            if await TaxRate.where("country", country).first() is None:
                await TaxRate.create(country=country, rate_bps=rate_bps)
