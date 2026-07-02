"""Application config — auto-loaded into ``config("app.*")`` at boot."""

from arvel import env

config = {
    "name": env("APP_NAME", "arvel"),
    "key": env("APP_KEY", ""),  # signing/crypto secret (arvel key:generate)
    "description": env("APP_DESCRIPTION", "A simple arvel application"),
    "version": env("APP_VERSION", "1.0.0"),
    "env": env("APP_ENV", "local"),
    "url": env("APP_URL", "http://localhost:8000"),
    "frontend_url": env("FRONTEND_URL", "http://localhost:5173"),
    "debug": env("APP_DEBUG", False),
    "timezone": "UTC",
}
