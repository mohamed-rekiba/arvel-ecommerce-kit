"""Create the carts table (owned by a user OR a guest cart token)."""

from arvel.database import Migration


class CreateCartsTable(Migration):
    def up(self, schema):
        def define(t):
            t.id()
            t.foreign_id("user_id").nullable().constrained("users").index()
            t.string("token").nullable().unique()  # guest cart token (when no user)
            t.timestamps()

        schema.create("carts", define)

    def down(self, schema):
        schema.drop("carts")
