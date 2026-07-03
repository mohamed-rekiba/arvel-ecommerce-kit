"""Account self-service — profile updates, password change, and email verification (S6).

Exercises arvel's auth flows (signed, expiring, purpose-bound email-verification tokens), the
`encrypted` model cast (phone is ciphertext at rest), the `hashed` cast + Hasher (current-password
confirmation), and the queued mail rail (verification mail).
"""

from arvel import abort
from arvel.auth.flows import email_verification_token, verify_email_token
from arvel.dates import Date
from arvel.http import Request
from arvel.security import Hasher
from arvel.support import current_user
from arvel.support.facades import Config, Mail
from arvel.validation import ValidationException, Validator

from app.mail.verify_email import VerifyEmail
from app.models.user import User
from app.schemas import (
    ChangePasswordIn,
    MessageOut,
    ProfileIn,
    UserOut,
    VerifyEmailIn,
)


def _me(request: Request) -> User:
    user = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    return user


async def avatar_url(user: User, conversion: str = "profile") -> str | None:
    """The user's avatar (a one-image media collection), as a serving URL — public-bucket URL
    when the disk exposes one, else the app-streamed /api/media route."""
    from app.models.user import AVATAR

    media = await user.get_media(AVATAR)
    if not media:
        return None
    url = media[0].get_url(conversion)
    if url and url.startswith(("http://", "https://")):
        return url
    return f"/api/media/{media[0].id}/{conversion}"


async def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        email_verified=user.email_verified_at is not None,
        avatar_url=await avatar_url(user),
        locale=str(getattr(user, "locale", None) or "en"),
    )


async def _send_verification(user: User) -> None:
    token = email_verification_token(user.id, str(Config.get("app.key", "")))
    await Mail.to(user.email).send(VerifyEmail(user.id, token))


async def update_profile(request: Request, data: ProfileIn) -> UserOut:
    """Update name/email/phone. Changing the email un-verifies the account and re-sends the
    verification link to the NEW address."""
    user = _me(request)
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
        raise ValidationException({"email": ["This email is already registered."]})

    user.name = payload["name"]
    user.email = payload["email"]
    if data.phone is not None:
        user.phone = data.phone or None  # empty string clears it
    if email_changed:
        user.email_verified_at = None
    await user.save()
    if email_changed:
        await _send_verification(user)
    return await _user_out(user)


async def change_password(request: Request, data: ChangePasswordIn) -> MessageOut:
    """Set a new password — only with the current one in hand (credential-change confirmation)."""
    user = _me(request)
    if len(data.password) < 8:
        raise ValidationException(
            {"password": ["The password must be at least 8 characters."]}
        )
    if not Hasher().check(data.current_password, user.password):
        raise ValidationException(
            {"current_password": ["That doesn't match your password."]}
        )
    user.password = data.password  # the `hashed` cast argon2-hashes on assignment
    await user.save()
    return MessageOut(message="Password updated.")


async def send_verification(request: Request) -> MessageOut:
    """(Re-)send the verification link to the account email."""
    user = _me(request)
    if user.email_verified_at is not None:
        return MessageOut(message="Your email is already verified.")
    await _send_verification(user)
    return MessageOut(message="Verification email sent.")


async def verify_email(request: Request, data: VerifyEmailIn) -> MessageOut:
    """Mark the account verified from a signed token (purpose-bound: a reset token won't pass)."""
    user_id = verify_email_token(data.token, str(Config.get("app.key", "")))
    user = await User.find(user_id) if user_id is not None else None
    if user is None:
        raise ValidationException(
            {"token": ["This verification link is invalid or has expired."]}
        )
    if user.email_verified_at is None:
        user.email_verified_at = Date.now()
        await user.save()
    return MessageOut(message="Email verified — welcome aboard!")


async def upload_avatar(request: Request) -> UserOut:
    """Attach/replace the account avatar (one image; the previous one is removed)."""
    from arvel.validation import ValidationException

    from app.models.user import AVATAR
    from app.services.product_image_service import ProductImageService

    user = _me(request)
    upload = await request.file("image")
    if upload is None:
        raise ValidationException({"image": ["An image file is required."]})
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
            {"image": ["The file is not a valid image."]}
        ) from exc
    for media in previous:
        await user.delete_media(media.id)
    return await _user_out(user)
