"""Create the remember_tokens table — persistent-login ("remember me") tokens via the
selector/validator pattern (arvel.auth.remember). A password reset revokes all of a user's
remember tokens, so the reset flow needs this table to exist."""

from arvel.database import Blueprint, Migration, Schema


class CreateRememberTokensTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.string("selector").unique()  # public handle → indexed single-row lookup
            t.string(
                "validator"
            )  # SHA-256 hash of the validator secret (never plaintext)
            t.big_integer("tokenable_id").index()  # the user; clear-all deletes by this
            t.datetime("expires_at")
            t.timestamps()

        schema.create("remember_tokens", define)

    def down(self, schema: Schema) -> None:
        schema.drop("remember_tokens")
