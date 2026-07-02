"""Hero banners — the public carousel feed (active slides, sorted, projected to the request
locale with an en fallback) and the admin CRUD + image upload that manages it."""

from typing import Any

from arvel import abort
from arvel.activitylog import activity
from arvel.http import Request
from arvel.support import current_user
from arvel.validation import ValidationException

from app.enums import Permission
from app.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, active_locale
from app.models.banner import HERO, Banner
from app.models.user import User
from app.schemas import (
    AdminBannerOut,
    BannerIn,
    BannerOut,
    BannerTextIn,
    BannerUpdateIn,
)
from app.services.product_image_service import ProductImageService


def _image_url(media: Any, conversion: str | None) -> str | None:
    if media is None:
        return None
    url = media.get_url(conversion)
    if url and url.startswith(("http://", "https://")):
        return url
    suffix = f"/{conversion}" if conversion else ""
    return f"/api/media/{media.id}{suffix}"


async def _first_media(banner: Banner) -> Any | None:
    media = await banner.get_media(HERO)
    return media[0] if media else None


def _text(banner: Banner, locale: str) -> dict[str, Any]:
    translations: dict[str, Any] = banner.translations or {}
    return translations.get(locale) or translations.get(DEFAULT_LOCALE) or {}


async def _public_out(banner: Banner, locale: str) -> BannerOut:
    media = await _first_media(banner)
    text = _text(banner, locale)
    return BannerOut(
        id=banner.id,
        title=str(text.get("title", "")),
        subtitle=text.get("subtitle"),
        chip=text.get("chip"),
        cta_label=text.get("cta_label"),
        cta_to=banner.cta_to or "/catalog",
        image_url=_image_url(media, "hero"),
        mobile_image_url=_image_url(media, "mobile"),
    )


async def index(request: Request) -> list[BannerOut]:
    locale = active_locale()
    banners = await Banner.where("active", True).order_by("sort").order_by("id").get()
    return [await _public_out(b, locale) for b in banners]


# --- admin -----------------------------------------------------------------------


def _current_user() -> User:
    user = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    return user


def _validated_translations(
    payload: dict[str, BannerTextIn] | None,
) -> dict[str, dict[str, Any]] | None:
    if payload is None:
        return None
    bad = [locale for locale in payload if locale not in SUPPORTED_LOCALES]
    if bad:
        raise ValidationException(
            {"translations": [f"Unsupported locale(s): {', '.join(sorted(bad))}."]}
        )
    if DEFAULT_LOCALE not in payload:
        raise ValidationException(
            {"translations": [f"The {DEFAULT_LOCALE} copy is required."]}
        )
    return {
        locale: {
            "title": text.title,
            "subtitle": text.subtitle,
            "chip": text.chip,
            "cta_label": text.cta_label,
        }
        for locale, text in payload.items()
    }


async def _admin_out(banner: Banner) -> AdminBannerOut:
    translations: dict[str, Any] = banner.translations or {}
    return AdminBannerOut(
        id=banner.id,
        translations={
            locale: BannerTextIn(
                title=str(fields.get("title", "")),
                subtitle=fields.get("subtitle"),
                chip=fields.get("chip"),
                cta_label=fields.get("cta_label"),
            )
            for locale, fields in translations.items()
        },
        cta_to=banner.cta_to or "/catalog",
        sort=banner.sort or 0,
        active=bool(banner.active),
        image_url=_image_url(await _first_media(banner), "hero"),
    )


async def admin_index(request: Request) -> list[AdminBannerOut]:
    user = _current_user()
    if not await user.can(Permission.CATALOG_VIEW.value):
        abort(403, "You lack catalog access.")
    return [
        await _admin_out(b) for b in await Banner.order_by("sort").order_by("id").get()
    ]


async def store(request: Request, data: BannerIn) -> AdminBannerOut:
    user = _current_user()
    if not await user.can(Permission.CATALOG_CREATE.value):
        abort(403, "You lack catalog access.")
    translations = _validated_translations(data.translations)
    banner = await Banner.create(
        translations=translations,
        cta_to=data.cta_to,
        sort=data.sort,
        active=data.active,
    )
    await activity().caused_by(user).performed_on(banner).log("created banner")
    return await _admin_out(banner)


async def update(request: Request, data: BannerUpdateIn) -> AdminBannerOut:
    user = _current_user()
    if not await user.can(Permission.CATALOG_UPDATE.value):
        abort(403, "You lack catalog access.")
    banner = await Banner.find_or_fail(int(request.path_param("id")))
    translations = _validated_translations(data.translations)
    if translations is not None:
        banner.translations = translations
    if data.cta_to is not None:
        banner.cta_to = data.cta_to
    if data.sort is not None:
        banner.sort = data.sort
    if data.active is not None:
        banner.active = data.active
    await banner.save()
    await activity().caused_by(user).performed_on(banner).log("updated banner")
    return await _admin_out(banner)


async def destroy(request: Request) -> dict[str, str]:
    user = _current_user()
    if not await user.can(Permission.CATALOG_DELETE.value):
        abort(403, "You lack catalog access.")
    banner = await Banner.find_or_fail(int(request.path_param("id")))
    for media in await banner.get_media(HERO):
        await banner.delete_media(media.id)
    await banner.delete()
    await activity().caused_by(user).performed_on(banner).log("deleted banner")
    return {"status": "deleted"}


async def upload_image(request: Request) -> AdminBannerOut:
    """Attach/replace the slide image (the previous one is removed — a slide has ONE image)."""
    user = _current_user()
    if not await user.can(Permission.CATALOG_UPDATE.value):
        abort(403, "You may not modify banner media.")
    banner = await Banner.find_or_fail(int(request.path_param("id")))
    upload = await request.file("image")
    if upload is None:
        raise ValidationException({"image": ["An image file is required."]})
    raw = await upload.read()
    previous = await banner.get_media(HERO)
    try:
        await ProductImageService().attach_uploaded(
            banner,
            raw,
            file_name=upload.client_name or "banner.png",
            mime_type=upload.content_type,
            collection=HERO,
        )
    except Exception as exc:  # noqa: BLE001 — any decode/store failure is a client error
        raise ValidationException(
            {"image": ["The file is not a valid image."]}
        ) from exc
    for media in previous:
        await banner.delete_media(media.id)
    return await _admin_out(banner)
