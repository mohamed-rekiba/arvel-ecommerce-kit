"""Newsletter signups (the reference's subscribe band) + the store settings KV that backs the
admin Settings page (topbar contact, welcome line, free-shipping threshold, …)."""

from arvel.database import Blueprint, Migration, Schema


class CreateNewsletterAndSettingsTables(Migration):
    def up(self, schema: Schema) -> None:
        def subscribers(t: Blueprint) -> None:
            t.id()
            t.string("email").unique()
            t.string("locale", 5).default(value="en")
            t.timestamps()

        schema.create("newsletter_subscribers", subscribers)

        def settings(t: Blueprint) -> None:
            t.id()
            t.string("key", 64).unique()
            t.text("value")
            t.timestamps()

        schema.create("settings", settings)

    def down(self, schema: Schema) -> None:
        schema.drop("settings")
        schema.drop("newsletter_subscribers")
