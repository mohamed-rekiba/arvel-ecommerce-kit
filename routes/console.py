"""Console (CLI) definitions — scheduled tasks + closure commands.

Loaded by the console kernel on every `arvel <command>` (not by the HTTP server).
"""

from arvel import Console, Schedule

from app.console.abandoned_carts import sweep_abandoned_carts
from app.console.search_reindex import search_reindex
from app.services.catalog_visibility_service import CatalogVisibilityService

# Nightly sweep of abandoned guest carts (run by `arvel schedule:run` via cron).
Schedule.call(sweep_abandoned_carts).daily_at("03:00")

# `arvel search:reindex` — rebuild the product search index (Scout's scout:import).
Console.command("search:reindex", search_reindex)

# Debounced catalog-visibility refresh: publish changes flag the views dirty (PublishObserver); this
# runs every minute and refreshes only if dirty (coalescing a burst into one CONCURRENTLY refresh).
Schedule.call(CatalogVisibilityService.refresh_if_dirty).every_minute()
