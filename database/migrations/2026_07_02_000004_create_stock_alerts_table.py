"""Back-in-stock subscriptions (S17) — one-shot: consumed when the restock notification fans out."""

from arvel.database import Blueprint, Migration, Schema


class CreateStockAlertsTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.foreign_id("product_variant_id").constrained("product_variants").index()
            t.foreign_id("user_id").constrained("users").index()
            t.timestamps()

        schema.create("stock_alerts", define)

    def down(self, schema: Schema) -> None:
        schema.drop("stock_alerts")
