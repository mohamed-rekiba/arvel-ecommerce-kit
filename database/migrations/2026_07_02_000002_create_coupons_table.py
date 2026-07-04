"""Coupons + redemptions. A coupon discounts the ORDER (one per order, order-level only);
redemptions record who used it (user id or guest email) so per-customer limits hold."""

from arvel.database import Blueprint, Migration, Schema


class CreateCouponsTable(Migration):
    def up(self, schema: Schema) -> None:
        def coupons(t: Blueprint) -> None:
            t.id()
            t.string("code", 40).unique()
            t.string("type", 10)  # CouponType: percent | fixed
            t.integer("value")  # percent points (1–100) or cents
            t.integer("min_subtotal_cents").default(value=0)
            t.datetime("starts_at").nullable()
            t.datetime("ends_at").nullable()
            t.integer("usage_limit").nullable()  # None = unlimited
            t.integer("per_customer_limit").nullable()
            t.integer("uses").default(value=0)
            t.boolean("active").default(value=True)
            t.boolean("announce").default(
                value=False
            )  # surfaced on the storefront announcement bar
            t.timestamps()

        schema.create("coupons", coupons)

        def redemptions(t: Blueprint) -> None:
            t.id()
            t.foreign_id("coupon_id").constrained("coupons").index()
            t.foreign_id("order_id").constrained("orders").index()
            t.foreign_id("user_id").nullable().constrained("users").index()
            t.string("contact_email").index()  # guests are limited by email
            t.timestamps()

        schema.create("coupon_redemptions", redemptions)

    def down(self, schema: Schema) -> None:
        schema.drop("coupon_redemptions")
        schema.drop("coupons")
