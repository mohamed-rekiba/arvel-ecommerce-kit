"""Create the personal access tokens table (bearer tokens — arvel.auth ApiToken)."""

from arvel.database import Blueprint, Migration, Schema


class CreatePersonalAccessTokensTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.string("name")
            t.string("token", 64).unique()
            t.big_integer("tokenable_id").index()
            t.text("abilities")
            t.datetime("expires_at").nullable()
            t.timestamps()

        schema.create("api_tokens", define)

    def down(self, schema: Schema) -> None:
        schema.drop("api_tokens")
