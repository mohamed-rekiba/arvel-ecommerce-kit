"""Account self-service (S6) — profile updates, password change with current-password
confirmation, email verification via signed purpose-bound tokens, and the encrypted phone cast —
all through the real served path."""

import asyncio
import secrets

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations
from arvel.support.facades import Mail
from arvel.testing import fake, reset_fakes

from app.mail.verify_email import VerifyEmail


@pytest.fixture
def faked_mail():
    mailer = fake(Mail)
    yield mailer
    reset_fakes()


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'account.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def migrate() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await db.dispose()

    asyncio.run(migrate())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _register(client, email="mira@example.com") -> dict:
    token = client.post(
        "/api/register",
        json={"name": "Mira", "email": email, "password": "supersecret"},
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_registration_sends_verification_and_the_link_verifies(
    client, faked_mail
) -> None:
    headers = _register(client)
    faked_mail.assert_sent(VerifyEmail)
    assert client.get("/api/user", headers=headers).json()["email_verified"] is False

    mail = faked_mail.sent[-1]
    assert (
        client.post(
            "/api/email/verify", json={"id": mail.user_id, "token": mail.token}
        ).status_code
        == 200
    )
    assert client.get("/api/user", headers=headers).json()["email_verified"] is True


def test_tampered_or_foreign_tokens_are_rejected(client, faked_mail) -> None:
    """A doctored link fails; an opaque non-verification token (e.g. a broker reset token) can't verify."""
    headers = _register(client)
    mail = faked_mail.sent[-1]

    tampered = client.post(
        "/api/email/verify", json={"id": mail.user_id, "token": mail.token[:-2] + "xx"}
    )
    assert tampered.status_code == 422

    # purpose isolation: an opaque token that isn't a signed verification token is rejected
    foreign = secrets.token_urlsafe(32)
    assert (
        client.post(
            "/api/email/verify", json={"id": mail.user_id, "token": foreign}
        ).status_code
        == 422
    )
    assert client.get("/api/user", headers=headers).json()["email_verified"] is False


def test_profile_update_and_email_change_reverifies(client, faked_mail) -> None:
    headers = _register(client)
    mail = faked_mail.sent[-1]
    client.post("/api/email/verify", json={"id": mail.user_id, "token": mail.token})

    # name + phone update; email untouched → stays verified
    updated = client.patch(
        "/api/user",
        json={"name": "Mira K", "phone": "+20 100 555 0199"},
        headers=headers,
    )
    assert updated.status_code == 200
    body = updated.json()
    assert (body["name"], body["phone"], body["email_verified"]) == (
        "Mira K",
        "+20 100 555 0199",
        True,
    )

    # email change → unverified + a fresh verification mail to the NEW address
    changed = client.patch(
        "/api/user", json={"email": "mira.new@example.com"}, headers=headers
    )
    assert changed.status_code == 200
    assert changed.json()["email_verified"] is False
    assert faked_mail.recipients[-1]["to"] == ["mira.new@example.com"]

    # a taken email is rejected
    _register(client, email="taken@example.com")
    assert (
        client.patch(
            "/api/user", json={"email": "taken@example.com"}, headers=headers
        ).status_code
        == 422
    )


def test_phone_is_ciphertext_at_rest(client, tmp_path) -> None:
    """The encrypted cast: the app reads the plaintext; the column stores ciphertext."""
    import sqlite3

    headers = _register(client)
    client.patch("/api/user", json={"phone": "+1 555 010 4477"}, headers=headers)
    assert client.get("/api/user", headers=headers).json()["phone"] == "+1 555 010 4477"

    raw = (
        sqlite3.connect(tmp_path / "account.sqlite")
        .execute("SELECT phone FROM users WHERE email = 'mira@example.com'")
        .fetchone()[0]
    )
    assert raw and "+1 555 010 4477" not in raw  # ciphertext, not the number


def test_password_change_requires_the_current_password(client) -> None:
    headers = _register(client)

    wrong = client.put(
        "/api/user/password",
        json={"current_password": "nope", "password": "another-secret"},
        headers=headers,
    )
    assert wrong.status_code == 422
    assert "current_password" in wrong.json()["errors"]

    ok = client.put(
        "/api/user/password",
        json={"current_password": "supersecret", "password": "another-secret"},
        headers=headers,
    )
    assert ok.status_code == 200

    # old credentials 401; new ones work
    assert (
        client.post(
            "/api/login", json={"email": "mira@example.com", "password": "supersecret"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/login",
            json={"email": "mira@example.com", "password": "another-secret"},
        ).status_code
        == 200
    )
