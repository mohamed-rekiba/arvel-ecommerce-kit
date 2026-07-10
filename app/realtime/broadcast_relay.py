"""BroadcastRelay — the app-owned ASGI websocket transport for K9 (DR-0066).

arvel ships the publish half (`ShouldBroadcast` → redis) and the channel-auth half
(`POST /broadcasting/auth`, HMAC-signed) of broadcasting; it deliberately doesn't ship a
browser-facing websocket server — its own docstring calls that "a driver extra". This relay *is*
that transport: it wraps the served ASGI app at the app-owned `asgi.py` seam (the same pattern
arvel's own `MethodOverride` uses to wrap non-HTTP scopes) and, on `/ws`, fans out arvel's redis
pub/sub to a native-WebSocket browser client.

It reuses arvel's own primitives rather than re-implementing them:
- a private-channel subscribe is authorized by calling arvel's own `verify_channel_auth`
  (DR-0067) — the relay never decides ownership itself, and it no longer even re-derives the HMAC
  construction: arvel owns sign AND verify, so a future signing change can't silently drift the
  relay's check out of sync. The deny decision (the 403 at `/broadcasting/auth`) is entirely
  arvel's; this only confirms the token presented is one arvel actually minted.
- the redis subscription reads arvel's own wire envelope (`{event, data, except_socket_id}`) and
  `accepts()` (arvel's own to_others()/echo-suppression rule).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import secrets
from collections.abc import Awaitable, Callable, MutableMapping
from typing import TYPE_CHECKING, Any, cast

from arvel.broadcasting import accepts
from arvel.routing import verify_channel_auth

if TYPE_CHECKING:
    from arvel.kernel import Application

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]

# arvel's own redis wire prefix (`RedisBroadcaster._CHANNEL_PREFIX` in arvel.broadcasting) — part
# of the publish contract, pinned here rather than reached into that private class attribute.
_CHANNEL_PREFIX = "arvel.broadcasting."
_WS_PATH = "/ws"


class BroadcastRelay:
    """ASGI middleware: intercepts the websocket scope at `/ws`; every other scope (http,
    lifespan, any other path) passes straight through to the wrapped app untouched."""

    def __init__(self, app: Application, inner: Any) -> None:
        self._app = app  # the booted Application (container) — for the redis facade
        self._inner = (
            inner  # the served ASGI app (litestar, already MethodOverride-wrapped)
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") == "websocket" and scope.get("path") == _WS_PATH:
            await self._serve(receive, send)
            return
        await self._inner(scope, receive, send)

    async def _serve(self, receive: Receive, send: Send) -> None:
        connect = await receive()
        if connect.get("type") != "websocket.connect":
            return
        await send({"type": "websocket.accept"})
        socket_id = secrets.token_urlsafe(16)

        # every outgoing frame funnels through one queue + one writer task, so concurrent
        # channel-relay tasks never race each other calling `send()` directly.
        outbox: asyncio.Queue[MutableMapping[str, Any]] = asyncio.Queue()
        await outbox.put(_text_frame({"event": "connected", "socket_id": socket_id}))
        writer = asyncio.create_task(self._drain(outbox, send))
        subscriptions: dict[str, asyncio.Task[None]] = {}
        try:
            while True:
                message = await receive()
                message_type = message.get("type")
                if message_type in ("websocket.disconnect", None):
                    break
                if message_type != "websocket.receive":
                    continue
                text = message.get("text")
                if isinstance(text, str) and text:
                    self._handle_subscribe(text, socket_id, outbox, subscriptions)
        finally:
            writer.cancel()
            for task in subscriptions.values():
                task.cancel()
            for task in (*subscriptions.values(), writer):
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    @staticmethod
    async def _drain(
        outbox: asyncio.Queue[MutableMapping[str, Any]], send: Send
    ) -> None:
        while True:
            await send(await outbox.get())

    def _handle_subscribe(
        self,
        text: str,
        socket_id: str,
        outbox: asyncio.Queue[MutableMapping[str, Any]],
        subscriptions: dict[str, asyncio.Task[None]],
    ) -> None:
        try:
            parsed: Any = json.loads(text)
        except ValueError:
            return
        if not isinstance(parsed, dict):
            return
        payload = cast("dict[str, Any]", parsed)
        if payload.get("event") != "subscribe":
            return
        channel = str(payload.get("channel") or "")
        if not channel or channel in subscriptions:
            return
        if channel.startswith("private-") and not verify_channel_auth(
            channel, socket_id, str(payload.get("auth") or "")
        ):
            outbox.put_nowait(
                _text_frame({"event": "subscribe_error", "channel": channel})
            )
            return
        subscriptions[channel] = asyncio.create_task(
            self._relay_channel(channel, socket_id, outbox)
        )

    async def _relay_channel(
        self,
        channel: str,
        socket_id: str,
        outbox: asyncio.Queue[MutableMapping[str, Any]],
    ) -> None:
        redis = self._app.make("redis")
        async for raw in redis.subscribe(f"{_CHANNEL_PREFIX}{channel}"):
            try:
                parsed: Any = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(parsed, dict):
                continue
            envelope = cast("dict[str, Any]", parsed)
            if not accepts(envelope, socket_id):
                continue
            await outbox.put(
                _text_frame(
                    {"event": envelope.get("event"), "data": envelope.get("data")}
                )
            )


def _text_frame(payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": "websocket.send", "text": json.dumps(payload)}
