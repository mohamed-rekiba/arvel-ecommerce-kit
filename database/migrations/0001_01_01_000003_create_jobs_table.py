"""Create the jobs table (database queue driver)."""

from arvel.database import Blueprint, Migration, Schema


class CreateJobsTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.string("queue").index()
            t.text("payload")
            t.integer("attempts")
            t.integer("reserved_at").nullable()
            t.integer(
                "reserved_until"
            ).nullable().index()  # effective visibility deadline
            t.integer("available_at")
            t.integer("created_at")

        schema.create("jobs", define)

    def down(self, schema: Schema) -> None:
        schema.drop("jobs")
