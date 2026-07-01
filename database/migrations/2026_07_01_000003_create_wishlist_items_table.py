"""Create the wishlist_items table — a customer's saved products (a user↔product pivot)."""

from arvel.database import Blueprint, Migration, Schema


class CreateWishlistItemsTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.foreign_id("user_id").constrained("users").index()
            t.foreign_id("product_id").constrained("products").index()
            t.timestamps()  # dedup is enforced in the controller (toggle checks before insert)

        schema.create("wishlist_items", define)

    def down(self, schema: Schema) -> None:
        schema.drop("wishlist_items")
