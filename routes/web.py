"""Web routes — stateful, browser-facing pages (the "web" group)."""

from arvel import Route
from arvel.routing import broadcast_websocket

# Realtime: the framework's built-in broadcast relay fans arvel's redis broadcast pub/sub out to
# browser clients over a websocket at the root path `/ws` (private channels gated by
# /broadcasting/auth). One line — no app-owned ASGI relay. Root-level (not under /api) so the SPA
# client connects to `/ws`.
Route.websocket("/ws", broadcast_websocket, name="ws.broadcast")
