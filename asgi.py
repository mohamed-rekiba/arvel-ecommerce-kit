"""ASGI entrypoint — `granian asgi:asgi_app` (or uvicorn)."""

from bootstrap.app import create_app

# The realtime websocket transport is a framework route now (`Route.websocket("/ws",
# broadcast_websocket)` in routes/api.py), so the app is served directly — no app-owned relay wrapper.
asgi_app = create_app().as_asgi()
