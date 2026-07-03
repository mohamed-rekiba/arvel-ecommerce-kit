"""The customer address book — saved shipping addresses with a single default per user.
Checkout can reference one by id (ownership-checked) instead of retyping the form."""

from arvel.database import Blueprint, Migration, Schema


class CreateAddressesTable(Migration):
    def up(self, schema: Schema) -> None:
        def addresses(t: Blueprint) -> None:
            t.id()
            t.foreign_id("user_id").constrained("users").index()
            t.string("label", 40).nullable()  # "Home", "Office", …
            t.string("name")
            t.string("line1")
            t.string("line2").nullable()
            t.string("city")
            t.string("postal_code", 20)
            t.string("country", 2)  # CountryCode enum at the API edge
            t.string("phone", 32).nullable()
            t.boolean("is_default").default(value=False)
            t.timestamps()

        schema.create("addresses", addresses)

    def down(self, schema: Schema) -> None:
        schema.drop("addresses")
