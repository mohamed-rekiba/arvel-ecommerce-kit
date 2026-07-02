"""Deals (flash sales) — a timed percent-off on ONE product. The storefront shows the struck
base price + deal price + countdown; the cart snapshots the deal price and checkout re-prices
every line to the price current at order time (deal_service is the single source of the math)."""

from arvel.database import Blueprint, Migration, Schema


class CreateDealsTable(Migration):
    def up(self, schema: Schema) -> None:
        def deals(t: Blueprint) -> None:
            t.id()
            t.foreign_id("product_id").constrained("products").index()
            t.integer("percent_off")  # 1–90, validated at the API edge
            t.datetime("starts_at")
            t.datetime("ends_at")
            t.boolean("active").default(value=True)
            t.timestamps()

        schema.create("deals", deals)

    def down(self, schema: Schema) -> None:
        schema.drop("deals")
