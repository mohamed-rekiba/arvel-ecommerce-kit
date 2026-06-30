"""Create the payments + webhook_events tables."""

from arvel.database import Blueprint, Migration, Schema


class CreatePaymentsTable(Migration):
    def up(self, schema: Schema) -> None:
        def payments(t: Blueprint) -> None:
            t.id()
            t.foreign_id("order_id").constrained("orders").index()
            t.string("gateway_charge_id").index()
            t.integer("amount_cents")
            t.string("status").default(value="pending").index()
            t.timestamps()

        schema.create("payments", payments)

        def webhook_events(t: Blueprint) -> None:
            t.id()
            t.string("event_id").unique()  # the idempotency key — unique across redeliveries
            t.string("type")
            t.timestamps()

        schema.create("webhook_events", webhook_events)

    def down(self, schema: Schema) -> None:
        schema.drop("webhook_events")
        schema.drop("payments")
