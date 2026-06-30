"""Create the products table."""

from arvel.database import Blueprint, Migration, Schema


class CreateProductsTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.foreign_id("category_id").constrained("categories").index()
            t.foreign_id("vendor_id").nullable().constrained("vendors").index()
            t.jsonb("name")  # translatable {locale: value} (HasTranslations / Translatable cast)
            t.string("slug").unique()
            t.text("description").nullable()  # (translatable description lands in the translations refactor)
            t.integer("price_cents")
            t.string("currency", length=3).default(value="USD")
            t.string("status").default(value="draft").index()
            t.boolean("published").default(value=False).index()  # retrievability: published ∧ vendor ∧ category-chain
            t.btree_index("name->>'en'")  # fast filter/sort on the English name (i18n)
            t.timestamps()
            # product images live in the media library (HasMedia / media table), not a column

        schema.create("products", define)

    def down(self, schema: Schema) -> None:
        schema.drop("products")
