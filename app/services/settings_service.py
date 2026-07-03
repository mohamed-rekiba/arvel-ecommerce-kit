"""Store settings — a cached key/value layer over the settings table. Reads ride
``Cache.remember`` (one query per cold key); every write invalidates. The PUBLIC set is the
whitelist the storefront may see; everything else is admin-only."""

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

    return dict(await Cache.remember(_CACHE_KEY, 300, _load))


async def update_settings(values: dict[str, str]) -> dict[str, str]:
    for key, value in values.items():
        if key not in DEFAULTS:
            continue  # the controller validates; this is belt-and-suspenders
        existing = await Setting.where("key", key).first()
        if existing is None:
            await Setting.create(key=key, value=value)
        else:
            existing.value = value
            await existing.save()
    await Cache.forget(_CACHE_KEY)
    return await all_settings()
