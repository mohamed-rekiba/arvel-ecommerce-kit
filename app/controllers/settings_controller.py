"""Store settings + newsletter — the public reads and the admin management surface."""

from arvel import abort
from app.auth.require import require_user as _admin
from arvel.http import Request
from arvel.validation import ValidationException, Validator

from app.controllers.serializers import iso as _iso
from app.enums import Permission
from app.i18n import active_locale, trans
from app.models.newsletter_subscriber import NewsletterSubscriber
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
    return MessageOut(message=trans("shop.messages.subscribed"))


async def admin_settings(request: Request) -> SettingsOut:
    user = _admin()
    if not await user.can(Permission.CATALOG_VIEW.value):
        abort(403, trans("shop.errors.no_catalog_access"))
    return SettingsOut(values=await settings_service.all_settings())


async def update_settings(request: Request, data: SettingsIn) -> SettingsOut:
    user = _admin()
    if not await user.can(Permission.CATALOG_UPDATE.value):
        abort(403, trans("shop.errors.no_catalog_access"))
    unknown = [k for k in data.values if k not in settings_service.DEFAULTS]
    if unknown:
        raise ValidationException(
            {
                "values": [
                    trans(
                        "shop.errors.unknown_settings",
                        settings=", ".join(sorted(unknown)),
                    )
                ]
            }
        )
    return SettingsOut(values=await settings_service.update_settings(data.values))


async def newsletter_index(request: Request) -> list[NewsletterSubscriberOut]:
    user = _admin()
    if not await user.can(Permission.CATALOG_VIEW.value):
        abort(403, trans("shop.errors.no_catalog_access"))
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
