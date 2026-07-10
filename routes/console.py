"""Console (CLI) definitions — scheduled tasks.

Loaded by the console kernel on every `arvel <command>` (not by the HTTP server).

`search:reindex` is registered elsewhere (`AppServiceProvider.commands()`) — it's a `Command`
subclass now, not a closure, so it belongs with the rest of provider-registered command classes,
not this closure/schedule file. See `app/console/search_reindex.py` for why.
"""

from arvel import Schedule

from app.console.abandoned_carts import sweep_abandoned_carts
from app.services.catalog_visibility_service import CatalogVisibilityService

# Nightly sweep of abandoned guest carts (run by `arvel schedule:run` via cron).
Schedule.call(sweep_abandoned_carts).daily_at("03:00")

# Debounced catalog-visibility refresh: publish changes flag the views dirty (PublishObserver); this
# runs every minute and refreshes only if dirty (coalescing a burst into one CONCURRENTLY refresh).
Schedule.call(CatalogVisibilityService.refresh_if_dirty).every_minute()
