"""Customer auth flow — register, login, current-user, logout (token revoke), and password reset —
through the real served HTTP path. Exercises arvel auth tokens/abilities, hashing, validation, and
the signed password-reset tokens.
"""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'auth.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv(
        "APP_DEBUG", "true"
    )  # exposes the reset token in the response (dev-only path)

    async def migrate() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await db.dispose()

    asyncio.run(migrate())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _register(client, email="ada@example.com", password="supersecret"):
    return client.post(
        "/api/register", json={"name": "Ada", "email": email, "password": password}
    )


def test_register_validates_and_issues_a_token(client) -> None:
    # invalid: short password + bad email
    bad = client.post(
        "/api/register", json={"name": "x", "email": "nope", "password": "short"}
    )
    assert bad.status_code == 422

    ok = _register(client)
    assert ok.status_code == 201
    token = ok.json()["token"]
    # the token unlocks the protected route
    me = client.get("/api/user", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"


def test_duplicate_email_is_rejected(client) -> None:
    assert _register(client).status_code == 201
    dup = _register(client)
    assert dup.status_code == 422


def test_login_then_logout_revokes_only_the_current_token(client) -> None:
    _register(client)
    a = client.post(
        "/api/login", json={"email": "ada@example.com", "password": "supersecret"}
    )
    b = client.post(
        "/api/login", json={"email": "ada@example.com", "password": "supersecret"}
    )
    token_a, token_b = a.json()["token"], b.json()["token"]

    # logout with token A revokes only A
    out = client.post("/api/logout", headers={"Authorization": f"Bearer {token_a}"})
    assert out.status_code == 200
    assert (
        client.get(
            "/api/user", headers={"Authorization": f"Bearer {token_a}"}
        ).status_code
        == 401
    )
    # token B still works (Sanctum: currentAccessToken()->delete() revokes just one)
    assert (
        client.get(
            "/api/user", headers={"Authorization": f"Bearer {token_b}"}
        ).status_code
        == 200
    )


def test_password_reset_flow(client) -> None:
    _register(client)
    # request a reset token (dev returns it; prod emails it)
    forgot = client.post("/api/forgot-password", json={"email": "ada@example.com"})
    assert forgot.status_code == 200
    reset_token = forgot.json()["reset_token"]

    # reset to a new password
    reset = client.post(
        "/api/reset-password", json={"token": reset_token, "password": "brandnewpass"}
    )
    assert reset.status_code == 200

    # old password rejected, new password works
    assert (
        client.post(
            "/api/login", json={"email": "ada@example.com", "password": "supersecret"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/login", json={"email": "ada@example.com", "password": "brandnewpass"}
        ).status_code
        == 200
    )


def test_forgot_password_is_non_enumerating(client) -> None:
    # an unknown email still returns 200 (no account-existence leak), without a reset token
    resp = client.post("/api/forgot-password", json={"email": "ghost@example.com"})
    assert resp.status_code == 200
    assert "reset_token" not in resp.json()
