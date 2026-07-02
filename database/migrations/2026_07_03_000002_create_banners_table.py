"""Hero banners — the admin-managed home carousel. Per-locale copy in a locale-major
``translations`` json (title/subtitle/chip/cta_label), a route path for the CTA, ordering, and an
active switch; the image itself rides the media library (``hero`` collection + conversions)."""

from arvel.database import Blueprint, Migration, Schema


class CreateBannersTable(Migration):
    def up(self, schema: Schema) -> None:
        def banners(t: Blueprint) -> None:
            t.id()
            t.jsonb("translations")  # {locale: {title, subtitle, chip, cta_label}}
            t.string("cta_to").default(value="/catalog")  # SPA route path
            t.integer("sort").default(value=0).index()
            t.boolean("active").default(value=True)
            t.timestamps()

        schema.create("banners", banners)

    def down(self, schema: Schema) -> None:
        schema.drop("banners")
