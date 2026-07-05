"""Store settings + newsletter — the public reads and the admin management surface."""

from arvel import abort
from arvel.http import Request
from arvel.support import current_user
from arvel.validation import ValidationException, Validator

from app.controllers.serializers import iso as _iso
from app.enums import Permission
from app.i18n import active_locale
from app.models.newsletter_subscriber import NewsletterSubscriber
from app.models.user import User
from app.schemas import (
    MessageOut,
    NewsletterIn,
    NewsletterSubscriberOut,
    SettingsIn,
    SettingsOut,
)
from app.services import settings_service


async def public_settings(request: Request) -> SettingsOut:
    values = await settings_service.all_settings()
    return SettingsOut(values={k: values[k] for k in settings_service.PUBLIC_KEYS})


async def subscribe(request: Request, data: NewsletterIn) -> MessageOut:
    """Idempotent newsletter signup — re-subscribing an existing email is a friendly 200."""
    email = data.email.strip().lower()
    validator = Validator({"email": email}, {"email": "required|email"})
    if validator.fails():
        raise ValidationException(dict(validator.errors()))
    if await NewsletterSubscriber.where("email", email).first() is None:
        await NewsletterSubscriber.create(email=email, locale=active_locale())
    return MessageOut(message="Subscribed.")


def _admin() -> User:
    user: User | None = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    return user


async def admin_settings(request: Request) -> SettingsOut:
    user = _admin()
    if not await user.can(Permission.CATALOG_VIEW.value):
        abort(403, "You lack catalog access.")
    return SettingsOut(values=await settings_service.all_settings())


async def update_settings(request: Request, data: SettingsIn) -> SettingsOut:
    user = _admin()
    if not await user.can(Permission.CATALOG_UPDATE.value):
        abort(403, "You lack catalog access.")
    unknown = [k for k in data.values if k not in settings_service.DEFAULTS]
    if unknown:
        raise ValidationException(
            {"values": [f"Unknown setting(s): {', '.join(sorted(unknown))}."]}
        )
    return SettingsOut(values=await settings_service.update_settings(data.values))


async def newsletter_index(request: Request) -> list[NewsletterSubscriberOut]:
    user = _admin()
    if not await user.can(Permission.CATALOG_VIEW.value):
        abort(403, "You lack catalog access.")
    rows = await NewsletterSubscriber.order_by("id", "desc").get()
    return [
        NewsletterSubscriberOut(
            id=r.id,
            email=r.email,
            locale=r.locale or "en",
            created_at=_iso(r.created_at),
        )
        for r in rows
    ]
