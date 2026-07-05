"""S6 — account self-service on real infra: the forgot→reset and register→verify round-trips ride
the queued mail rail (RabbitMQ worker → Mailpit), and the encrypted phone is ciphertext in the raw
Postgres column."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx
import pytest

from tests.integration.test_queue_rail import _run_worker, _seed_shop

pytestmark = pytest.mark.integration


def _link_from_mail(api: str, subject_part: str) -> str:
    """Fetch the newest Mailpit message matching the subject and pull the first link out of it."""
    messages = httpx.get(f"{api}/api/v1/messages").json()["messages"]
    match = next(m for m in messages if subject_part in m["Subject"])
    body = httpx.get(f"{api}/api/v1/message/{match['ID']}").json()["HTML"]
    href = re.search(r'href="([^"]+)"', body)
    assert href, body
    return href.group(1)


def _link_query(link: str) -> dict[str, str]:
    """The query params of a mailed link (id/token/email) as a flat dict."""
    from urllib.parse import parse_qs, urlparse

    return {k: v[0] for k, v in parse_qs(urlparse(link).query).items()}


def test_reset_and_verification_round_trips_on_real_mail(
    postgres_url: str,
    rabbitmq_url: str,
    mailpit: dict[str, Any],
    kit_app: Any,
) -> None:
    asyncio.run(_seed_shop(postgres_url))
    env = dict(
        DATABASE_URL=postgres_url,
        QUEUE_CONNECTION="amqp",
        QUEUE_URL=rabbitmq_url,
        MAIL_MAILER="smtp",
        MAIL_HOST=str(mailpit["host"]),
        MAIL_PORT=str(mailpit["smtp_port"]),
    )
    with kit_app(**env) as client:
        # register → a queued verification mail
        token = client.post(
            "/api/register",
            json={"name": "Rio", "email": "rio@example.com", "password": "supersecret"},
        ).json()["token"]
        auth = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/user", headers=auth).json()["email_verified"] is False

        # forgot password → a queued reset mail (non-enumerating both ways)
        assert (
            client.post(
                "/api/forgot-password", json={"email": "rio@example.com"}
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/forgot-password", json={"email": "ghost@example.com"}
            ).status_code
            == 200
        )

    async def _both_delivered() -> bool:
        subjects = [
            m["Subject"]
            for m in httpx.get(f"{mailpit['api']}/api/v1/messages").json()["messages"]
        ]
        return any("Verify" in s for s in subjects) and any(
            "Reset" in s for s in subjects
        )

    asyncio.run(_run_worker(30.0, until=_both_delivered))

    verify_q = _link_query(_link_from_mail(mailpit["api"], "Verify"))
    reset_q = _link_query(_link_from_mail(mailpit["api"], "Reset"))

    with kit_app(**env) as client:
        # the emailed verification link (id + token) verifies the account
        assert (
            client.post(
                "/api/email/verify",
                json={"id": int(verify_q["id"]), "token": verify_q["token"]},
            ).status_code
            == 200
        )

        # the emailed reset link (email + token) sets a new password; the old one stops working
        assert (
            client.post(
                "/api/reset-password",
                json={
                    "email": reset_q["email"],
                    "token": reset_q["token"],
                    "password": "a-new-password",
                },
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/login",
                json={"email": "rio@example.com", "password": "supersecret"},
            ).status_code
            == 401
        )
        fresh = client.post(
            "/api/login",
            json={"email": "rio@example.com", "password": "a-new-password"},
        )
        assert fresh.status_code == 200
        auth = {"Authorization": f"Bearer {fresh.json()['token']}"}
        assert client.get("/api/user", headers=auth).json()["email_verified"] is True

        # encrypted PII: plaintext through the app, ciphertext in the raw PG column
        client.patch("/api/user", json={"phone": "+20 100 555 0123"}, headers=auth)
        assert (
            client.get("/api/user", headers=auth).json()["phone"] == "+20 100 555 0123"
        )

    async def _raw_phone() -> str:
        import sqlalchemy as sa
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(postgres_url)
        async with engine.connect() as conn:
            row = await conn.execute(
                sa.text("SELECT phone FROM users WHERE email = 'rio@example.com'")
            )
            value = row.scalar_one()
        await engine.dispose()
        return str(value)

    raw = asyncio.run(_raw_phone())
    assert raw and "+20 100 555 0123" not in raw  # ciphertext at rest
