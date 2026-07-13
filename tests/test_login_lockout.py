"""Login brute-force lockout — repeated wrong-password attempts for one account lock it out.

Exercised through the real HTTP path (a seeded sqlite file the served app reads), the same way the
rest of the auth flow is tested. Fails if the credential-specific lockout is removed: without it,
the sixth attempt is a plain 401 (or a 200 for the right password), never a 429.
"""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.models.user import User


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'lockout.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        User.set_connection(db)
        await User.create(name="Victim", email="victim@example.com", password="correct-horse")
        await User.create(name="Other", email="other@example.com", password="hunter2")
        User.set_connection(None)
        await db.dispose()

    asyncio.run(seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _attempt(client, email, password):
    return client.post("/api/login", json={"email": email, "password": password})


def test_five_failures_lock_the_account(client) -> None:
    for _ in range(5):
        assert _attempt(client, "victim@example.com", "wrong").status_code == 401
    # sixth attempt is locked out even WITH the correct password
    locked = _attempt(client, "victim@example.com", "correct-horse")
    assert locked.status_code == 429
    assert int(locked.headers["retry-after"]) > 0


def test_lockout_is_per_account_not_global(client) -> None:
    for _ in range(5):
        _attempt(client, "victim@example.com", "wrong")
    # a different account from the same client is unaffected
    assert _attempt(client, "other@example.com", "hunter2").status_code == 200


def test_a_good_login_before_the_cap_clears_the_counter(client) -> None:
    for _ in range(4):  # one below the cap
        assert _attempt(client, "victim@example.com", "wrong").status_code == 401
    assert _attempt(client, "victim@example.com", "correct-horse").status_code == 200  # clears
    # counter reset: four more failures don't lock (would if the good login hadn't cleared it)
    for _ in range(4):
        assert _attempt(client, "victim@example.com", "wrong").status_code == 401
