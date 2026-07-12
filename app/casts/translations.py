"""Casts for the locale-major `translations` jsonb column (`{"en": {...}, "fr": {...}}`).

`TranslationsCast` maps the whole column to `list[Translate]` (admin); `TranslationCast` maps a
single locale projection to one `Translate` (storefront). Both go through `__casts__`, so
controllers never (de)serialize translations by hand.
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

    def get(
        self, model: Any, key: str, value: Any, attributes: dict[str, Any]
    ) -> list[Translate]:
        return [_translate(locale, fields) for locale, fields in _load(value).items()]

    def set(self, model: Any, key: str, value: Any, attributes: dict[str, Any]) -> Any:
        if isinstance(value, list):
            return {
                t.locale: {"name": t.name, "description": t.description}
                for t in cast("list[Translate]", value)
            }
        return value


class LocaleMapCast:
    """A locale-major jsonb map with free-form per-locale fields ↔ plain dict — handles the
    PG-dict / sqlite-string asymmetry without imposing the Translate shape."""

    def get(
        self, model: Any, key: str, value: Any, attributes: dict[str, Any]
    ) -> dict[str, Any]:
        return _load(value)

    def set(self, model: Any, key: str, value: Any, attributes: dict[str, Any]) -> Any:
        return value


class TranslationCast:
    """A single locale's object `{name, description}` (a `translations->'<loc>'` projection) →
    `Translate`. The sibling `translation_locale` projection says which locale the COALESCE
    served (requested, or the default fallback) — surfaced so API consumers can tell."""

    def get(
        self, model: Any, key: str, value: Any, attributes: dict[str, Any]
    ) -> Translate:
        return _translate(str(attributes.get("translation_locale") or ""), _load(value))

    def set(self, model: Any, key: str, value: Any, attributes: dict[str, Any]) -> Any:
        return value
