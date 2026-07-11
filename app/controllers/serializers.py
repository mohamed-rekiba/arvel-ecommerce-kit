"""Shared response-shaping helpers for the API controllers."""

from typing import Any


def iso(value: Any) -> str | None:
    """A timestamp → a JSON-safe ISO-8601 string, whether it's an arvel Date
    (``to_iso_string`` — the framework's RFC-3339 instant form) or a stdlib datetime."""
    if value is None:
        return None
    for attr in ("to_iso_string", "isoformat"):
        fn = getattr(value, attr, None)
        if callable(fn):
            return str(fn())
    return str(value)
