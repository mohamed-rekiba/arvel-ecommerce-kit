"""Create the categories table (self-referencing for nested taxonomy)."""

from arvel.database import Blueprint, Migration, Schema


class CreateCategoriesTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.string("name")
            t.string("slug").unique()
            t.foreign_id("parent_id").nullable().constrained("categories")
            t.boolean("published").default(value=True)  # admin intent; retrievability also needs ancestors published
            t.timestamps()

        schema.create("categories", define)

    def down(self, schema: Schema) -> None:
        schema.drop("categories")
