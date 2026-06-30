"""Create the failed_jobs table (records jobs that exhausted their retries)."""

from arvel.database import Blueprint, Migration, Schema


class CreateFailedJobsTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.uuid("id").primary()
            t.string("queue").index()
            t.text("payload")
            t.text("exception")
            t.timestamp("failed_at")

        schema.create("failed_jobs", define)

    def down(self, schema: Schema) -> None:
        schema.drop("failed_jobs")
