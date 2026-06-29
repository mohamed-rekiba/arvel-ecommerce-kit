"""Create the product_variants table."""

from arvel.database import Migration


class CreateProductVariantsTable(Migration):
    def up(self, schema):
        def define(t):
            t.id()
            t.foreign_id("product_id").constrained("products").index()
            t.string("sku").unique()
            t.string("name")
            t.integer("price_adjustment_cents").default(value=0)
            t.integer("stock").default(value=0)
            t.timestamps()

        schema.create("product_variants", define)

    def down(self, schema):
        schema.drop("product_variants")
