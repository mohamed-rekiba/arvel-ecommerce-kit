"""Shared response-shaping helpers for the API controllers."""

from typing import Any


def iso(value: Any) -> str | None:
    """A timestamp → a *standard* ISO-8601 string, whether it's an arvel Date (``to_iso``) or a
    stdlib datetime. arvel's ``to_iso`` appends an RFC-9557 ``[UTC]`` zone-name annotation that JS
    ``Date`` and most parsers reject, so we strip it (the numeric ``+00:00`` offset already carries
    the zone)."""
    if value is None:
        return None
    for attr in ("to_iso", "isoformat"):
        fn = getattr(value, attr, None)
        if callable(fn):
            return str(fn()).split("[", 1)[0]
    return str(value)
