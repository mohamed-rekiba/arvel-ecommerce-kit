"""Broadcasting config — the driver `ShouldBroadcast` events publish through.

`redis` publishes to the shared Valkey pub/sub (the same instance `CACHE_URL` points at by
default — see `config/cache.py`); `log` (arvel's own default) just records sends, no network. The
unit test tier forces `log` (tests/conftest.py) so tests never touch real infra.
"""

from arvel import env

config = {
    "default": env("BROADCAST_CONNECTION", "redis"),
}
