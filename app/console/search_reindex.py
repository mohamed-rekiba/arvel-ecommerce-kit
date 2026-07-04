"""Console command: rebuild the product search index (`arvel search:reindex`).

Use after a bulk load or `db:seed` to (re)populate the configured search engine.
"""

from app.models.product import Product


async def search_reindex() -> None:
    count = await Product.make_all_searchable()
    print(f"Reindexed {count} products into the search engine.")
