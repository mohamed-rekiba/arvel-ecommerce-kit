"""Console (CLI) definitions — scheduled tasks + closure commands (cf. Laravel's routes/console.php).

Loaded by the console kernel on every `arvel <command>` (not by the HTTP server).

Scheduled tasks — run by `arvel schedule:run` (point a once-a-minute cron at it):

    from arvel import Schedule

    Schedule.command("queue:work --stop-when-empty").hourly()
    Schedule.call(prune_old_exports).daily_at("02:00")

Closure commands (Laravel `Artisan::command`) — appear in `arvel --help` and run through the booted
app (handler args come from the CLI; everything else is autowired from the container):

    from arvel import Console

    async def greet(name: str):
        print(f"Hello, {name}!")

    Console.command("greet {name}", greet)   # $ arvel greet Ada  ->  Hello, Ada!

Signature tokens: `{arg}` (required), `{arg?}` (optional), `{--flag}` (boolean option). For larger
commands, prefer a class via `arvel make:command` (type-safe, DI-aware).
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
