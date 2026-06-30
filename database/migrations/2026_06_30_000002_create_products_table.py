"""Create the products table."""

from arvel.database import Blueprint, Migration, Schema


class CreateProductsTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.foreign_id("category_id").constrained("categories").index()
            t.string("name")
            t.string("slug").unique()
            t.text("description").nullable()
            t.integer("price_cents")
            t.string("currency", length=3).default(value="USD")
            t.string("status").default(value="draft").index()
            t.string("image_path").nullable()  # original image path on the Storage disk
            t.string("image_thumb_path").nullable()  # generated thumbnail (arvel.media)
            t.timestamps()

        schema.create("products", define)

    def down(self, schema: Schema) -> None:
        schema.drop("products")
