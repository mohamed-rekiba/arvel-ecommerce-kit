"""K9 — the framework relay's enforcement of a private-channel subscribe (the
`verify_channel_auth` branch in `arvel.routing.broadcast_websocket`): a forged or non-ASCII
(DR-0067's fail-closed guard) token gets `subscribe_error`, never a subscription. This is the
actual gate — a client can't fabricate a token to subscribe — distinct from the HTTP-side 403
`/broadcasting/auth` returns (proven in `test_order_broadcast.py`). Hermetic: no Docker, no real
redis (a denied private channel never touches it). The `/ws` transport is a framework route now.
"""

import pytest
from litestar.testing import TestClient


@pytest.fixture
def relay_client():
    from bootstrap.app import create_app

    app = create_app()
    with TestClient(app=app.as_asgi()) as client:
        yield client


@pytest.mark.parametrize("forged_auth", ["deadbeef" * 8, "ünïcödé-not-ascii"])
def test_relay_denies_a_forged_or_non_ascii_private_subscribe(
    relay_client, forged_auth
) -> None:
    with relay_client.websocket_connect("/ws") as ws:
        connected = ws.receive_json()
        assert connected["event"] == "connected"

        ws.send_json(
            {"event": "subscribe", "channel": "private-order.1", "auth": forged_auth}
        )
        frame = ws.receive_json()
        assert frame == {"event": "subscribe_error", "channel": "private-order.1"}
