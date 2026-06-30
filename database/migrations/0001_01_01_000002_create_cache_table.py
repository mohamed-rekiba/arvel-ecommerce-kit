"""Create the cache table (database cache driver)."""

from arvel.database import Blueprint, Migration, Schema


class CreateCacheTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.string("key").unique()
            t.text("value")
            t.integer("expiration")

        schema.create("cache", define)

    def down(self, schema: Schema) -> None:
        schema.drop("cache")
