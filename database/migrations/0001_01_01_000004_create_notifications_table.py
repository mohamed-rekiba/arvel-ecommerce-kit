"""Create the notifications table (database notification channel)."""

from arvel.database import Blueprint, Migration, Schema


class CreateNotificationsTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.uuid("id").primary()
            t.string("type")
            t.string("notifiable_type")
            t.string("notifiable_id").index()
            t.text("data")
            t.timestamp("read_at").nullable()
            t.timestamps()

        schema.create("notifications", define)

    def down(self, schema: Schema) -> None:
        schema.drop("notifications")
