"""K15 — refunds table. A `Refund` reverses one SUCCEEDED `Payment` through the mock PSP boundary
(mirrors `payments`). The partial unique index is the DB-level backstop for the money invariant
(guard 1 of refund_service.initiate_refund's three-guard idempotency, DR-0065): at most one LIVE
(pending/succeeded) refund per order, even if the app-level `FOR UPDATE` were ever bypassed. It's
partial, not a plain unique on order_id, so a FAILED reverse-call attempt doesn't permanently block
a legitimate retry — only an in-flight or completed refund blocks a second one."""

import sqlalchemy as sa

from arvel.database import Blueprint, Migration, Schema


class CreateRefundsTable(Migration):
    def up(self, schema: Schema) -> None:
        def refunds(t: Blueprint) -> None:
            t.id()
            t.foreign_id("order_id").constrained("orders").index()
            t.foreign_id("payment_id").constrained("payments").index()
            t.string("gateway_charge_id").index()  # the charge being reversed
            t.string(
                "gateway_refund_id"
            ).nullable()  # set once the gateway POST answers
            t.integer("amount_cents")
            t.string("status").default(value="pending").index()
            t.boolean("restock").default(value=False)
            t.timestamps()

        schema.create("refunds", refunds)
        schema.execute(
            sa.text(
                "CREATE UNIQUE INDEX refunds_order_active_idx ON refunds (order_id) "
                "WHERE status IN ('pending', 'succeeded')"
            )
        )

    def down(self, schema: Schema) -> None:
        schema.drop("refunds")
