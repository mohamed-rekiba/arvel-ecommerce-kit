"""Console command: rebuild the product search index.

`arvel search:reindex` — (re)indexes every product into the configured search engine (Meilisearch in
production; the in-process array engine otherwise). This is the parity of Laravel Scout's
`scout:import`, and the reliable way to (re)populate the index after a bulk load or `db:seed`.
"""

from app.models.product import Product


async def search_reindex() -> None:
    count = await Product.make_all_searchable()
    print(f"Reindexed {count} products into the search engine.")
