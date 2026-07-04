"""Session config.

`driver`: anything but "redis" keeps arvel's in-process session store (lost on restart, not
shared across workers). "redis" backs sessions with the app's own bound `Cache` service — the
same Valkey connection already used for caching (config/cache.py), not a second one — so sessions
survive restarts and are shared across every worker/host (`arvel.http.kernel.use_default_groups`).
"""

from arvel import env

config = {
    "driver": env("SESSION_DRIVER", "redis"),  # cookie (in-process) | redis
    "lifetime": 120,  # minutes (Laravel parity); x60 for cookie max-age
    "secure": env("SESSION_SECURE", False),
}
