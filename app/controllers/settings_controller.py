"""Store settings + newsletter — the public reads and the admin management surface."""

from arvel.http import Request
from arvel.validation import ValidationException

from app.controllers.serializers import iso as _iso
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
    # normalized by NewsletterIn.prepare_for_validation; re-subscribing is a no-op
    await NewsletterSubscriber.first_or_create(
        {"email": data.email}, {"locale": active_locale()}
    )
    return MessageOut(message=trans("shop.messages.subscribed"))


async def admin_settings(request: Request) -> SettingsOut:
    return SettingsOut(values=await settings_service.all_settings())


async def update_settings(request: Request, data: SettingsIn) -> SettingsOut:
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
