"""Storefront locales — the single source of truth.

Content is stored locale-major (``translations`` jsonb: ``{"en": {...}, "fr": {...}, "ar": {...}}``)
and projected per request. Every SQL/projection path resolves the request locale through
``active_locale()`` so an unsupported ``Accept-Language`` degrades to the default locale everywhere
(projection, search, admin validation) instead of behaving differently per code path.
"""

from arvel.localization import current_locale

SUPPORTED_LOCALES: frozenset[str] = frozenset({"en", "fr", "ar"})
DEFAULT_LOCALE = "en"


def active_locale() -> str:
    """The request's locale (set by LocaleMiddleware from Accept-Language / the user preference),
    whitelisted to SUPPORTED_LOCALES with a fallback to the default."""
    locale = current_locale.get()
    return locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
