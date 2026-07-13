"""Account self-service — profile updates, password change, and email verification.

Phone is stored via the `encrypted` cast (ciphertext at rest); password checks go through the
`hashed` cast + Hasher.
"""

from app.i18n import trans
from arvel.auth.flows import email_verification_token, verify_email_token
from arvel.dates import Date
from arvel.http import Request
from arvel.security import Hasher
from arvel.support.facades import Config, Mail
from arvel.validation import ValidationException, Validator

from app.auth.require import require_user
from app.mail.verify_email import VerifyEmail
from app.models.user import User
from app.schemas import (
    ChangePasswordIn,
    MessageOut,
    ProfileIn,
    UserOut,
    VerifyEmailIn,
)


async def avatar_url(user: User, conversion: str = "profile") -> str | None:
    """The user's avatar (a one-image media collection), as a serving URL."""
    from app.models.user import AVATAR

    media = await user.get_media(AVATAR)
    return media[0].serving_url(conversion) if media else None


async def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        email_verified=user.email_verified_at is not None,
        avatar_url=await avatar_url(user),
        locale=str(getattr(user, "mail_locale", None) or "en"),
    )


async def _send_verification(user: User) -> None:
    token = email_verification_token(
        user.id, user.email, str(Config.get("app.key", ""))
    )
    await Mail.to(user.email).send(
        VerifyEmail(
            user.id, token, locale=str(getattr(user, "mail_locale", None) or "en")
        )
    )


async def update_profile(request: Request, data: ProfileIn) -> UserOut:
    """Update name/email/phone. Changing the email un-verifies the account and re-sends the
    verification link to the NEW address."""
    user = require_user()
    payload = {
        "name": data.name if data.name is not None else user.name,
        "email": data.email if data.email is not None else user.email,
    }
    validator = Validator(
        payload, {"name": "required|string", "email": "required|email"}
    )
    if validator.fails():
        raise ValidationException(validator.errors())

    email_changed = payload["email"] != user.email
    if (
        email_changed
        and await User.where("email", payload["email"]).first() is not None
    ):
        raise ValidationException({"email": [trans("shop.errors.email_taken")]})

    user.name = payload["name"]
    user.email = payload["email"]
    if data.phone is not None:
        user.phone = data.phone or None  # empty string clears it
    if email_changed:
        user.email_verified_at = None
    await user.save()
    if email_changed:
        await _send_verification(user)
    return await user_out(user)


async def change_password(request: Request, data: ChangePasswordIn) -> MessageOut:
    """Set a new password — only with the current one in hand (credential-change confirmation)."""
    user = require_user()
    if len(data.password) < 8:
        raise ValidationException(
            {"password": [trans("shop.errors.password_too_short")]}
        )
    if not Hasher().check(data.current_password, user.password):
        raise ValidationException(
            {"current_password": [trans("shop.errors.password_mismatch")]}
        )
    user.password = data.password  # the `hashed` cast argon2-hashes on assignment
    await user.save()
    return MessageOut(message=trans("shop.messages.password_updated"))


async def send_verification(request: Request) -> MessageOut:
    """(Re-)send the verification link to the account email."""
    user = require_user()
    if user.email_verified_at is not None:
        return MessageOut(message=trans("shop.messages.email_already_verified"))
    await _send_verification(user)
    return MessageOut(message=trans("shop.messages.verification_sent"))


async def verify_email(request: Request, data: VerifyEmailIn) -> MessageOut:
    """Mark the account verified from a signed token (purpose-bound: a reset token won't pass).
    The token is bound to the email it was issued for, so it stops verifying once the address
    changes — we load the user the link names, then check the token against their current email."""
    user = await User.find(data.id)
    verified_id = (
        verify_email_token(data.token, user.email, str(Config.get("app.key", "")))
        if user is not None
        else None
    )
    # verify_email_token returns the id in string form (so UUID/ULID keys work), so compare as str
    if user is None or verified_id != str(user.id):
        raise ValidationException(
            {"token": [trans("shop.errors.verification_link_invalid")]}
        )
    if user.email_verified_at is None:
        user.email_verified_at = Date.now()
        await user.save()
    return MessageOut(message=trans("shop.messages.email_verified"))


async def upload_avatar(request: Request) -> UserOut:
    """Attach/replace the account avatar (one image; the previous one is removed)."""
    from arvel.validation import ValidationException

    from app.models.user import AVATAR
    from app.services.product_image_service import ProductImageService

    user = require_user()
    upload = await request.file("image")
    if upload is None:
        raise ValidationException({"image": [trans("shop.errors.image_required")]})
    raw = await upload.read()
    previous = await user.get_media(AVATAR)
    try:
        await ProductImageService().attach_uploaded(
            user,
            raw,
            file_name=upload.client_name or "avatar.png",
            mime_type=upload.content_type,
            collection=AVATAR,
        )
    except Exception as exc:  # noqa: BLE001 — any decode/store failure is a client error
        raise ValidationException(
            {"image": [trans("shop.errors.file_not_image")]}
        ) from exc
    for media in previous:
        await user.delete_media(media.id)
    return await user_out(user)
