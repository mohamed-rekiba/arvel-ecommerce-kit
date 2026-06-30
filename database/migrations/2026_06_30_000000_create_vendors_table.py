"""Create the vendors table — a product's seller. A product is only retrievable when its vendor is
published (see the retrievable_products materialized view)."""

from arvel.database import Blueprint, Migration, Schema


class CreateVendorsTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.string("name")
            t.string("slug").unique()
            t.boolean("published").default(value=True)
            t.timestamps()

        schema.create("vendors", define)

    def down(self, schema: Schema) -> None:
        schema.drop("vendors")
