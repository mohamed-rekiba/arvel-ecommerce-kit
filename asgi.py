"""ASGI entrypoint — `granian asgi:asgi_app` (or uvicorn)."""

from bootstrap.app import create_app

from app.realtime.broadcast_relay import BroadcastRelay

_app = create_app()
# BroadcastRelay wraps the served app at this same seam arvel's own MethodOverride uses (non-HTTP
# scopes pass straight through) — it's the K9 websocket transport (DR-0066), not a framework route.
asgi_app = BroadcastRelay(_app, _app.as_asgi())
