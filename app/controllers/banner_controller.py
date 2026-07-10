"""Hero banners — the public carousel feed (active slides, sorted, projected to the request
locale with an en fallback) and the admin CRUD + image upload that manages it."""

from typing import Any, cast

from arvel import abort
from arvel.activitylog import activity
from arvel.auth.middleware import Authorize
from arvel.http import Request
from arvel.routing import Controller, ControllerMiddleware
from arvel.support import current_user
from arvel.validation import ValidationException

from app.enums import Permission
from app.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, active_locale, trans
from app.models.media import AppMedia
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


async def _first_media(banner: Banner) -> AppMedia | None:
    # get_media() is typed to base Media, but Banner.__media_model__ makes the rows AppMedia
    media = await banner.get_media(HERO)
    return cast("AppMedia", media[0]) if media else None


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
        image_url=media.serving_url("hero") if media else None,
        mobile_image_url=media.serving_url("mobile") if media else None,
    )


async def index(request: Request) -> list[BannerOut]:
    locale = active_locale()
    banners = await Banner.where("active", True).order_by("sort").order_by("id").get()
    return [await _public_out(b, locale) for b in banners]


# --- admin ---


def _current_user() -> User:
    user: User | None = current_user.get()
    if user is None:
        abort(401, trans("shop.errors.unauthenticated"))
    return user


def _validated_translations(
    payload: dict[str, BannerTextIn] | None,
) -> dict[str, dict[str, Any]] | None:
    if payload is None:
        return None
    bad = [locale for locale in payload if locale not in SUPPORTED_LOCALES]
    if bad:
        raise ValidationException(
            {
                "translations": [
                    trans(
                        "shop.errors.unsupported_locales",
                        locales=", ".join(sorted(bad)),
                    )
                ]
            }
        )
    if DEFAULT_LOCALE not in payload:
        raise ValidationException(
            {
                "translations": [
                    trans("shop.errors.default_copy_required", lang=DEFAULT_LOCALE)
                ]
            }
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
    media = await _first_media(banner)
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
        image_url=media.serving_url("hero") if media else None,
    )


class BannerController(Controller):
    """Admin banner CRUD. Every action here carries a declared ``Authorize`` (DR-0055) — reviewed
    as a whole resource, not just the id-bound ones, so the surface has one consistent authz
    posture; K5 relocates index/store/update/destroy's declaration from per-route to
    per-controller. ``update`` used to stay an explicit route (see ``CategoryController``'s
    docstring for why: arvel's resource generator bound ``update`` to both PUT and PATCH, which
    tripped Litestar's OpenAPI operationId-uniqueness check); that's fixed at the framework level
    now (DR-0057), so it's declared here like every other action."""

    @classmethod
    def middleware(cls) -> list[ControllerMiddleware]:
        return [
            ControllerMiddleware(
                Authorize(Permission.CATALOG_VIEW.value), only=("index",)
            ),
            ControllerMiddleware(
                Authorize(Permission.CATALOG_CREATE.value), only=("store",)
            ),
            ControllerMiddleware(
                Authorize(Permission.CATALOG_UPDATE.value), only=("update",)
            ),
            ControllerMiddleware(
                Authorize(Permission.CATALOG_DELETE.value), only=("destroy",)
            ),
        ]

    async def index(self, request: Request) -> list[AdminBannerOut]:
        return [
            await _admin_out(b)
            for b in await Banner.order_by("sort").order_by("id").get()
        ]

    async def store(self, request: Request, data: BannerIn) -> AdminBannerOut:
        user = _current_user()
        translations = _validated_translations(data.translations)
        banner = await Banner.create(
            translations=translations,
            cta_to=data.cta_to,
            sort=data.sort,
            active=data.active,
        )
        await activity().caused_by(user).performed_on(banner).log("created banner")
        return await _admin_out(banner)

    async def update(
        self, request: Request, banner: Banner, data: BannerUpdateIn
    ) -> AdminBannerOut:
        user = _current_user()
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

    async def destroy(self, request: Request, banner: Banner) -> dict[str, str]:
        user = _current_user()
        for media in await banner.get_media(HERO):
            await banner.delete_media(media.id)
        await banner.delete()
        await activity().caused_by(user).performed_on(banner).log("deleted banner")
        return {"status": "deleted"}


async def upload_image(request: Request, id: Banner) -> AdminBannerOut:
    """Attach/replace the slide image (the previous one is removed — a slide has ONE image)."""
    banner = id
    upload = await request.file("image")
    if upload is None:
        raise ValidationException({"image": [trans("shop.errors.image_required")]})
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
            {"image": [trans("shop.errors.file_not_image")]}
        ) from exc
    for media in previous:
        await banner.delete_media(media.id)
    return await _admin_out(banner)
