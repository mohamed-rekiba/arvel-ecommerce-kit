# Operability runbook — maintenance mode & scheduled tasks

Copy-paste-and-see-it. Everything below runs against the compose stack (`make up`).

## Maintenance mode (`arvel down` / `arvel up`)

```bash
uv run arvel down            # the shop returns 503 everywhere…
curl -i localhost:8000/api/products | head -1   # HTTP/1.1 503
curl -i localhost:8000/api/health   | head -1   # HTTP/1.1 200 — the probe stays up
uv run arvel up              # …and comes back
curl -i localhost:8000/api/products | head -1   # HTTP/1.1 200
```

- The flag lives in the **default cache store**. With the kit's Valkey cache every process sees
  `down` at once and it survives restarts; with the in-process `array` driver it's local to one
  process.
- Exempt paths come from `config/app.py → maintenance_except` (the kit exempts `/api/health` so
  load balancers keep probing).
- The Vue storefront turns the 503 into a designed “Back in a moment” screen with a retry button —
  no raw JSON reaches a shopper.

## Scheduled tasks (`arvel schedule:run`)

Point a once-a-minute cron at the runner:

```cron
* * * * * cd /path/to/arvel-ecommerce-kit && uv run arvel schedule:run >> storage/schedule.log 2>&1
```

What's registered (see `routes/console.py`):

| Task | Cadence | What it does |
|------|---------|--------------|
| `sweep_abandoned_carts` | daily at 03:00 | deletes GUEST carts idle >72h (user carts never) |
| `CatalogVisibilityService.refresh_if_dirty` | every minute | if a publish/archive change flagged the views dirty, one `REFRESH MATERIALIZED VIEW CONCURRENTLY` (single-flighted via `Cache.lock`); clean ticks no-op |

Try it now:

```bash
uv run arvel schedule:run      # ran N due task(s)
```

- A **failing task never kills the tick** — it's logged (`scheduled_task_failed` on the
  `schedule` channel) and the remaining events still run.
- `make schedule` is a shortcut for a single run.

## Queues (companion runbook)

Order mail/notifications ride the worker: `make worker` (`arvel queue:work`). Failures land in
`failed_jobs` — `uv run arvel queue:failed` to inspect, `uv run arvel queue:retry <id|all>` to
re-dispatch. See the README's “Queued mail & notifications”.
