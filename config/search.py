"""Search config — the catalog full-text engine.

`array` (in-process, the default + test driver) needs nothing. `meilisearch` (the `[search]` extra)
indexes into a real Meilisearch — see docker-compose.yml (:7700). A `Searchable` model is mirrored
into the index on save and queried via `Model.search(q)`.
"""

from arvel import env

config = {
    "driver": env("SEARCH_DRIVER", "array"),  # "array" | "meilisearch"
    "meilisearch": {
        "url": env("MEILISEARCH_URL", "http://localhost:7700"),
        "key": env("MEILISEARCH_KEY", None),
    },
}
