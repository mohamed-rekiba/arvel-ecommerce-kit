"""The activity_log table backing arvel's ActivityLogger — the
admin audit trail (who did what to which subject, with a property diff)."""

from arvel.database import Blueprint, Migration, Schema


class CreateActivityLogTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.string("log_name").nullable().index()
            t.text("description")
            t.string("subject_type").nullable()
            t.integer("subject_id").nullable().index()
            t.string("causer_type").nullable()
            t.integer("causer_id").nullable().index()
            t.string("event").nullable()
            t.text("properties").nullable()  # "json"-cast field ⇒ text column
            t.string("batch_uuid").nullable()
            t.timestamps()

        schema.create("activity_log", define)

    def down(self, schema: Schema) -> None:
        schema.drop("activity_log")
