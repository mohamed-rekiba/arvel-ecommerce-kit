"""Create the users table."""

from arvel.database import Blueprint, Migration, Schema


class CreateUsersTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.string("name")
            t.string("email").unique()
            t.datetime(
                "email_verified_at"
            ).nullable()  # set when the user verifies their email
            t.string("password")
            # PII stored via arvel's `encrypted` cast — ciphertext at rest, so text-sized
            t.text("phone").nullable()
            t.string("role").default(
                value="customer"
            ).index()  # customer | admin (UserRole)
            t.timestamps()

        schema.create("users", define)

    def down(self, schema: Schema) -> None:
        schema.drop("users")
