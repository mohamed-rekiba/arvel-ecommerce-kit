"""Create the categories table (self-referencing for nested taxonomy)."""

from arvel.database import Migration


class CreateCategoriesTable(Migration):
    def up(self, schema):
        def define(t):
            t.id()
            t.string("name")
            t.string("slug").unique()
            t.foreign_id("parent_id").nullable().constrained("categories")
            t.timestamps()

        schema.create("categories", define)

    def down(self, schema):
        schema.drop("categories")
