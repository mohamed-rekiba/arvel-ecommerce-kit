"""Create the password_reset_tokens table — the stored, single-use, per-email throttled reset
token the PasswordBroker keys by email (replaces the old stateless signed-token reset)."""

from arvel.database import Blueprint, Migration, Schema


class CreatePasswordResetTokensTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.string("email").primary()  # one active token per email; a new send replaces it
            t.string("token_hash")  # Hasher hash of the reset token — never the plaintext
            t.datetime("created_at")  # drives both the per-email throttle and the TTL expiry

        schema.create("password_reset_tokens", define)

    def down(self, schema: Schema) -> None:
        schema.drop("password_reset_tokens")
