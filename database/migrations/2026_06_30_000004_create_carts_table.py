"""Create the carts table (owned by a user OR a guest cart token)."""

from arvel.database import Blueprint, Migration, Schema


class CreateCartsTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.foreign_id("user_id").nullable().constrained("users").index()
            t.string("token").nullable().unique()  # guest cart token (when no user)
            t.timestamps()

        schema.create("carts", define)

    def down(self, schema: Schema) -> None:
        schema.drop("carts")
