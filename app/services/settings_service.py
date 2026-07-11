"""Store settings — a cached key/value layer over the settings table. Reads ride
stale-while-revalidate (``Cache.flexible``): a just-expired key serves the last value instantly
and refreshes once in the background instead of blocking the request; every write invalidates.
The PUBLIC set is the whitelist the storefront may see; everything else is admin-only."""

from arvel import Cache

from app.models.setting import Setting

# key → default. The whitelist doubles as the schema: unknown keys are rejected at the edge.
DEFAULTS: dict[str, str] = {
    "store.email": "shop@arvel.test",
    "store.phone": "+1 (086) 123-5678",
    "store.welcome": "",  # empty = the storefront falls back to its i18n key
    "store.free_shipping_over": "79",  # dollars, shown in the trust strip
}
PUBLIC_KEYS = tuple(DEFAULTS)

_CACHE_KEY = "settings:all"


async def all_settings() -> dict[str, str]:
    async def _load() -> dict[str, str]:
        rows = await Setting.all()
        stored = {r.key: r.value for r in rows}
        return {key: stored.get(key, default) for key, default in DEFAULTS.items()}

    # stale-while-revalidate: within 300s serve fresh; 300-600s serve the last value instantly and
    # refresh once in the background instead of blocking on Setting.all(). Accepted tradeoff: a
    # revalidation whose read races an admin edit can briefly resurrect the pre-edit value (bounded by
    # the 300s fresh window, self-heals on the next edit) — fine for low-stakes display settings.
    return dict(await Cache.flexible(_CACHE_KEY, (300, 600), _load))


async def update_settings(values: dict[str, str]) -> dict[str, str]:
    for key, value in values.items():
        if key not in DEFAULTS:
            continue  # the controller validates; this is belt-and-suspenders
        await Setting.update_or_create({"key": key}, {"value": value})
    await Cache.forget(_CACHE_KEY)
    return await all_settings()
