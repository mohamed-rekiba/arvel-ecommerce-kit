"""Create the media table — backs arvel's media library (HasMedia / add_media → media collections).

A polymorphic store: each row is one file attached to a model (model_type/model_id) in a named
collection, with its generated conversions (thumbnails) recorded as JSON.
"""

from arvel.database import Blueprint, Migration, Schema


class CreateMediaTable(Migration):
    def up(self, schema: Schema) -> None:
        def define(t: Blueprint) -> None:
            t.id()
            t.string("model_type").index()
            t.big_integer("model_id").index()
            t.string("collection_name").index()
            t.string("name")
            t.string("file_name")
            t.string("mime_type")
            t.string("disk")
            t.big_integer("size")
            # TEXT, not json: arvel's Media model casts these with the "json" cast, which owns
            # serialization (json.dumps/loads) — a native json column double-binds and rejects the
            # text the cast produces.
            t.text("custom_properties")
            t.text("generated_conversions")
            t.integer("order_column").default(value=0)
            t.timestamps()

        schema.create("media", define)

    def down(self, schema: Schema) -> None:
        schema.drop("media")
