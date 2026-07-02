"""Create the orders + order_items tables."""

from arvel.database import Blueprint, Migration, Schema


class CreateOrdersTable(Migration):
    def up(self, schema: Schema) -> None:
        def orders(t: Blueprint) -> None:
            t.id()
            t.foreign_id("user_id").nullable().constrained("users").index()
            t.string("status").default(value="pending").index()
            # contact + shipping address captured at checkout (guests included — it's how their
            # order mail reaches them); line2 is the only optional part of an address
            t.string("contact_email")
            t.string("ship_name")
            t.string("ship_line1")
            t.string("ship_line2").nullable()
            t.string("ship_city")
            t.string("ship_postal_code")
            t.string("ship_country", 2)
            # the server-computed money breakdown: subtotal + shipping + tax = total
            t.integer("subtotal_cents")
            t.integer("shipping_cents")
            t.integer("tax_cents")
            t.integer("total_cents")
            t.string("currency", 3)
            t.timestamps()

        schema.create("orders", orders)

        def order_items(t: Blueprint) -> None:
            t.id()
            t.foreign_id("order_id").constrained("orders").index()
            t.foreign_id("product_variant_id").constrained("product_variants").index()
            t.integer("quantity")
            t.integer("unit_price_cents")
            t.timestamps()

        schema.create("order_items", order_items)

    def down(self, schema: Schema) -> None:
        schema.drop("order_items")
        schema.drop("orders")
