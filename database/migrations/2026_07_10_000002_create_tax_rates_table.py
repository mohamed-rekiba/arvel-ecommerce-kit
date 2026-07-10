"""K17 — tax by jurisdiction. `tax_rates` keys the checkout tax rate by shipping country (the only
geo field an address/order carries — no region/state column exists). Rate is stored as **integer
basis points** (700 = 7.00%), not a Decimal column — float-free and keeps the story kit-only
(DR-0063). Also adds `orders.tax_rate_bps`, the rate actually applied to that order, so a stored
`tax_cents` is self-explaining. `.default(value=1000)` backfills existing rows to today's flat 10%
so the ADD is safe on the populated `orders` table."""

from arvel.database import Blueprint, Migration, Schema


class CreateTaxRatesTable(Migration):
    def up(self, schema: Schema) -> None:
        def tax_rates(t: Blueprint) -> None:
            t.id()
            t.string("country", 2).unique()  # ISO alpha-2; one rate per country
            t.integer("rate_bps")  # basis points: 700 = 7.00%
            t.timestamps()

        schema.create("tax_rates", tax_rates)

        def add_tax_rate_bps(t: Blueprint) -> None:
            t.integer("tax_rate_bps").default(value=1000)

        schema.table("orders", add_tax_rate_bps)

    def down(self, schema: Schema) -> None:
        schema.drop_column("orders", "tax_rate_bps")
        schema.drop("tax_rates")
