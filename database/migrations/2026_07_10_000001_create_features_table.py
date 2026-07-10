"""Feature flags (K14) — the `database` driver's backing table for the feature-flag subsystem:
one resolved value per flag name + scope, persisted so a runtime toggle (a console/portal call)
is visible to every process without a redeploy. Shape matches the framework's own skeleton
migration. `value` is TEXT, not native json: the ORM's json-cast fields always bind as TEXT
(_build_table's TEXT_CASTS contract, to avoid double-encoding), so the column must agree —
DR-0062."""

from arvel.database import Blueprint, Migration, Schema


class CreateFeaturesTable(Migration):
    def up(self, schema: Schema) -> None:
        def features(t: Blueprint) -> None:
            t.id()
            t.string("name")
            t.string("scope")
            t.text("value").nullable()
            t.timestamps()
            t.unique_index("name", "scope")  # one stored value per flag+scope

        schema.create("features", features)

    def down(self, schema: Schema) -> None:
        schema.drop("features")
