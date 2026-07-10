"""Console command: rebuild the product search index (`arvel search:reindex`).

Use after a bulk load or `db:seed` to (re)populate the configured search engine.

A `Command` subclass, not a closure: a closure's `output: ConsoleOutput` param gets autowired by
the container, which recurses into `ConsoleOutput.__init__`'s own `out: TextIO | None = None`
param — and since `typing.TextIO` is a real (non-abstract, non-Protocol) class, the container
builds a `TextIO()` stub for it instead of using the `None` default. That stub's `.write()` is a
silent no-op, so the command emits nothing. `Command.__init__` builds `ConsoleOutput()` as a plain
Python call (never through the container), so it never hits this edge — registered via
`AppServiceProvider.commands()` (DR-0034's own pattern), not `routes/console.py`.
"""

from typing import Any

from arvel.console import Command

from app.models.product import Product


class SearchReindexCommand(Command):
    signature = "search:reindex"
    description = "Rebuild the product search index."

    async def handle(
        self, *_deps: Any
    ) -> None:  # no deps needed; matches Command.handle's shape
        count = await Product.make_all_searchable()
        self.info(f"Reindexed {count} products into the search engine.")
