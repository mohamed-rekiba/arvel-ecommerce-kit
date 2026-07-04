"""Cache config — the default store + its connection.

`array` (in-process, the default) needs nothing; `redis` needs a `url` and the `[redis]` extra —
point `CACHE_URL` at your Redis.
"""

from arvel import env

config = {
    "default": env("CACHE_STORE", "array"),  # "array" (in-process) | "redis"
    "url": env("CACHE_URL", "redis://localhost:6379/0"),  # used by the redis store
}
