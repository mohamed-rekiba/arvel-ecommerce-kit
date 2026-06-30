"""Create the products table."""

from arvel.database import Migration


class CreateProductsTable(Migration):
    def up(self, schema):
        def define(t):
            t.id()
            t.foreign_id("category_id").constrained("categories").index()
            t.string("name")
            t.string("slug").unique()
            t.text("description").nullable()
            t.integer("price_cents")
            t.string("currency", length=3).default(value="USD")
            t.string("status").default(value="draft").index()
            t.string("image_path").nullable()  # path on the Storage disk (set on image upload)
            t.timestamps()

        schema.create("products", define)

    def down(self, schema):
        schema.drop("products")
