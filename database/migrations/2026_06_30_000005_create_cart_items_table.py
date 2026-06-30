"""Create the cart_items table."""

from arvel.database import Migration


class CreateCartItemsTable(Migration):
    def up(self, schema):
        def define(t):
            t.id()
            t.foreign_id("cart_id").constrained("carts").index()
            t.foreign_id("product_variant_id").constrained("product_variants").index()
            t.integer("quantity")
            t.integer("unit_price_cents")
            t.timestamps()

        schema.create("cart_items", define)

    def down(self, schema):
        schema.drop("cart_items")
