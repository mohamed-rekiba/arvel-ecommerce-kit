"""Create the product_variants table."""

from arvel.database import Blueprint, Migration, Schema


class CreateProductVariantsTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.foreign_id("product_id").constrained("products").index()
            t.string("sku").unique()
            t.string("name")
            t.integer("price_adjustment_cents").default(value=0)
            t.integer("stock").default(value=0)
            t.timestamps()

        schema.create("product_variants", define)

    def down(self, schema: Schema) -> None:
        schema.drop("product_variants")
