"""Product reviews — polymorphic subject (morphs), moderated. One review per customer per
subject; the aggregate (sum + count of APPROVED ratings) is denormalized onto products so listing
reads take zero extra queries."""

from arvel.database import Blueprint, Migration, Schema


class CreateReviewsTable(Migration):
    def up(self, schema: Schema) -> None:
        def reviews(t: Blueprint) -> None:
            t.id()
            t.morphs(
                "subject"
            )  # subject_type + subject_id (Product today; morphable by design)
            t.foreign_id("user_id").constrained("users").index()
            t.integer("rating")  # 1–5 (validated at the boundary)
            t.string("title").nullable()
            t.text("body")
            t.string("status", 10).default(value="pending").index()  # ReviewStatus
            t.timestamps()

        schema.create("reviews", reviews)

        def add_aggregates(t: Blueprint) -> None:
            t.integer("rating_sum").default(value=0)
            t.integer("rating_count").default(value=0)

        schema.table("products", add_aggregates)

    def down(self, schema: Schema) -> None:
        schema.drop_column("products", "rating_sum", "rating_count")
        schema.drop("reviews")
