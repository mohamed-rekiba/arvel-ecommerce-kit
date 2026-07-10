"""K16 — selectable shipping methods. `shipping_methods` keys the checkout shipping rate by a
method CODE the customer picks (standard/express), not by weight or zone — there is no weight
column on products/variants and no sub-country zone on an address (the same limit K17 hit for tax).
Rate is stored as a flat **integer cents** amount per method (DR-0064), not Decimal — float-free and
keeps the story kit-only. Also adds `orders.shipping_method` (the method actually charged, so a
stored `shipping_cents` is self-explaining) and `orders.tracking_number` (set on the ship
transition). `.default(value="standard")` backfills existing order rows so the ADD is safe on the
populated `orders` table; `tracking_number` is nullable (pre-ship and historical orders have none)."""

from arvel.database import Blueprint, Migration, Schema


class CreateShippingMethodsTable(Migration):
    def up(self, schema: Schema) -> None:
        def shipping_methods(t: Blueprint) -> None:
            t.id()
            t.string(
                "code"
            ).unique()  # 'standard' | 'express' — the code the client selects
            t.string("name")  # display label ('Standard', 'Express')
            t.integer("rate_cents")  # flat per-method amount (no weight/zone) — DR-0064
            t.boolean("active").default(value=True)
            t.integer("sort").default(value=0)
            t.timestamps()

        schema.create("shipping_methods", shipping_methods)

        def add_order_columns(t: Blueprint) -> None:
            t.string("shipping_method").default(value="standard")
            t.string("tracking_number").nullable()

        schema.table("orders", add_order_columns)

    def down(self, schema: Schema) -> None:
        schema.drop_column("orders", "shipping_method", "tracking_number")
        schema.drop("shipping_methods")
