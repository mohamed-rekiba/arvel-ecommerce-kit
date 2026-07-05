"""Customer authentication — registration, login (token issue), logout (token revoke), and the
password-reset flow.
"""

from typing import Any

from arvel import abort
from arvel.auth.flows import email_verification_token
from arvel.auth.password_reset import PasswordBroker, PasswordResetStatus
from arvel.auth.tokens import TokenGuard, create_token
from arvel.http import Request
from arvel.support.facades import Config, Mail
from arvel.validation import ValidationException, Validator

from app.controllers.cart_controller import merge_guest_cart
from app.mail.verify_email import VerifyEmail
from app.models.user import User
from app.schemas import (
    ForgotPasswordIn,
    ForgotPasswordOut,
    MessageOut,
    RegisterIn,
    ResetPasswordIn,
    TokenOut,
)

# Customer tokens are scoped to the "customer" ability (admins authenticate via OIDC, not here).
CUSTOMER_ABILITY = "customer"


def _password_broker() -> PasswordBroker:
    """The stored, single-use password-reset broker keyed by email. ``send_reset_link`` stores a
    hashed token and fires ``PasswordResetRequested`` — the app's listener (registered in
    ``AppServiceProvider.boot``) sends the actual email."""

    async def _lookup(email: str) -> Any:
        return await User.where("email", email).first()

    return PasswordBroker(_lookup)


async def register(request: Request, data: RegisterIn) -> TokenOut:
    """Register a customer and issue a scoped API token."""
    payload = {"name": data.name, "email": data.email, "password": data.password}
    validator = Validator(
        payload,
        {
            "name": "required|string",
            "email": "required|email",
            "password": "required|string|min:8",
        },
    )
    if validator.fails():
        raise ValidationException(validator.errors())
    if await User.where("email", data.email).first() is not None:
        raise ValidationException({"email": ["This email is already registered."]})
    from app.i18n import active_locale

    user = await User.create(
        name=data.name,
        email=data.email,
        password=data.password,
        locale=active_locale(),
    )
    await merge_guest_cart(
        request, user
    )  # a guest's cart follows them into the new account
    verification = email_verification_token(
        user.id, user.email, str(Config.get("app.key", ""))
    )
    await Mail.to(user.email).send(VerifyEmail(user.id, verification))
    token, _ = await create_token(user, name="customer", abilities=[CUSTOMER_ABILITY])
    return TokenOut(token=token)


async def logout(request: Request) -> MessageOut:
    """Revoke only the current token (Sanctum currentAccessToken()->delete())."""
    token = await TokenGuard().token(request)
    if token is None:
        abort(401, "Unauthenticated")
    await token.delete()
    return MessageOut(message="Logged out.")


async def forgot_password(
    request: Request, data: ForgotPasswordIn
) -> ForgotPasswordOut:
    """Store a single-use reset token and email its link. Always 200 (non-enumerating)."""
    # the broker stores a hashed token + fires PasswordResetRequested (the listener emails the link);
    # its INVALID_USER/RESET_THROTTLED status stays internal — the response never reveals it (DR-0033).
    await _password_broker().send_reset_link(data.email)
    return ForgotPasswordOut(
        message="If that email exists, a reset link has been sent."
    )


async def _set_password(user: Any, new_password: str) -> None:
    user.password = (
        new_password  # the User model's `hashed` cast argon2-hashes on assignment
    )
    await user.save()


async def reset_password(request: Request, data: ResetPasswordIn) -> MessageOut:
    """Consume the single-use reset token and set the new (hashed) password."""
    if len(data.password) < 8:
        raise ValidationException(
            {"password": ["The password must be at least 8 characters."]}
        )
    status = await _password_broker().reset(
        data.email, data.token, data.password, _set_password
    )
    if status is not PasswordResetStatus.RESET_SUCCESS:
        raise ValidationException(
            {"token": ["This password reset token is invalid or has expired."]}
        )
    return MessageOut(message="Password has been reset.")
