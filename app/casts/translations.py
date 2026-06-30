"""Custom casts for the single locale-major `translations` jsonb column
(`{"en": {"name","description"}, "fr": {...}}`).

- `TranslationsCast` — the whole column → `list[Translate]` (one per locale), for the admin.
- `TranslationCast` — a single locale's object (the `scope_in_locale` projection `translations->'<loc>'`)
  → a single `Translate`, for the storefront.

Both go through the model cast system (`__casts__`), so controllers never (de)serialize translations by hand.
"""

from __future__ import annotations

import json
from typing import Any, cast

from app.schemas import Translate


def _load(value: Any) -> dict[str, Any]:
    """The stored jsonb as a dict — a dict on Postgres, a JSON string on sqlite."""
    if isinstance(value, str):
        return json.loads(value) if value else {}
    return dict(value) if value else {}


def _translate(locale: str, fields: dict[str, Any]) -> Translate:
    return Translate(
        name=str(fields.get("name", "")),
        description=fields.get("description"),
        locale=locale,
    )


class TranslationsCast:
    """jsonb `{locale: {name, description}}` ↔ `list[Translate]`."""

    def get(self, model: Any, key: str, value: Any, attributes: dict[str, Any]) -> list[Translate]:
        return [_translate(locale, fields) for locale, fields in _load(value).items()]

    def set(self, model: Any, key: str, value: Any, attributes: dict[str, Any]) -> Any:
        if isinstance(value, list):  # list[Translate] → locale-major dict
            return {
                t.locale: {"name": t.name, "description": t.description}
                for t in cast("list[Translate]", value)
            }
        return value  # a locale-major dict → stored as-is (the jsonb column serializes it)


class TranslationCast:
    """A single locale's object `{name, description}` (a `translations->'<loc>'` projection) → `Translate`."""

    def get(self, model: Any, key: str, value: Any, attributes: dict[str, Any]) -> Translate:
        return _translate("", _load(value))

    def set(self, model: Any, key: str, value: Any, attributes: dict[str, Any]) -> Any:
        return value
