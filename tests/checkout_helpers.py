"""Shared checkout fixtures — a valid checkout submission (S3: contact + address are required)."""

from typing import Any


def checkout_body(email: str | None = None, **overrides: Any) -> dict[str, Any]:
    """A valid checkout payload; pass ``email`` for guests (signed-in users default to their
    account email) and keyword overrides to poke holes in it."""
    body: dict[str, Any] = {
        "address": {
            "name": "Cara Lund",
            "line1": "12 Linen Way",
            "line2": None,
            "city": "Portland",
            "postal_code": "97201",
            "country": "US",
        }
    }
    if email is not None:
        body["email"] = email
    body.update(overrides)
    return body
