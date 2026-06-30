"""Create the orders + order_items tables."""

from arvel.database import Migration


class CreateOrdersTable(Migration):
    def up(self, schema):
        def orders(t):
            t.id()
            t.foreign_id("user_id").nullable().constrained("users").index()
            t.string("status").default(value="pending").index()
            t.integer("total_cents")
            t.timestamps()

        schema.create("orders", orders)

        def order_items(t):
            t.id()
            t.foreign_id("order_id").constrained("orders").index()
            t.foreign_id("product_variant_id").constrained("product_variants").index()
            t.integer("quantity")
            t.integer("unit_price_cents")
            t.timestamps()

        schema.create("order_items", order_items)

    def down(self, schema):
        schema.drop("order_items")
        schema.drop("orders")
