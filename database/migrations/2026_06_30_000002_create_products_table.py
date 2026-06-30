"""Create the products table."""

from arvel.database import Blueprint, Migration, Schema


class CreateProductsTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.foreign_id("category_id").constrained("categories").index()
            t.foreign_id("vendor_id").nullable().constrained("vendors").index()
            t.string("slug").unique()
            # ONE translatable column, locale-major: {"en": {"name","description"}, "fr": {...}}
            t.jsonb("translations")
            t.integer("price_cents")
            t.string("currency", length=3).default(value="USD")
            t.string("status").default(value="draft").index()
            t.boolean("published").default(value=False).index()  # retrievability: published ∧ vendor ∧ category-chain
            t.btree_index("translations->'en'->>'name'")  # fast filter/sort on the English name (i18n)
            t.timestamps()
            # product images live in the media library (HasMedia / media table), not a column

        schema.create("products", define)

    def down(self, schema: Schema) -> None:
        schema.drop("products")
