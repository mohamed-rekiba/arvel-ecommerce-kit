"""Redis config — the raw redis facade's connection (`arvel.cache.redis.RedisManager`, bound as
`"redis"`). Distinct from `config/cache.py` (the *cache abstraction*, cashews): this is the
direct-command facade the K9 broadcasting `redis` driver and the websocket relay publish/subscribe
through. Defaults to the same Valkey instance `CACHE_URL` points at — override independently
(e.g. in the integration tier, a throwaway testcontainer) via `REDIS_URL`.
"""

from arvel import env

config = {
    "url": env("REDIS_URL", "redis://localhost:6379/0"),
}
