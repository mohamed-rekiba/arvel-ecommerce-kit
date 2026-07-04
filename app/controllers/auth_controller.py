"""Customer authentication — registration, login (token issue), logout (token revoke), and the
password-reset flow.
"""

from arvel import abort
from arvel.auth.flows import (
    email_verification_token,
    password_reset_token,
    verify_password_reset_token,
)
from arvel.auth.tokens import TokenGuard, create_token
from arvel.http import Request
from arvel.support.facades import Config, Mail
from arvel.validation import ValidationException, Validator

from app.controllers.cart_controller import merge_guest_cart
from app.mail.password_reset import PasswordReset
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
    verification = email_verification_token(user.id, str(Config.get("app.key", "")))
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
    """Issue a signed password-reset token. Always 200 (non-enumerating); a real app emails it."""
    user = await User.where("email", data.email).first()
    if user is not None:
        token = password_reset_token(user.id, str(Config.get("app.key", "")))
        await Mail.to(user.email).send(PasswordReset(user.email, token))
    # identical response either way — the endpoint never reveals whether the email exists
    return ForgotPasswordOut(
        message="If that email exists, a reset link has been sent."
    )


async def reset_password(request: Request, data: ResetPasswordIn) -> MessageOut:
    """Verify the signed reset token and set the new (hashed) password."""
    if len(data.password) < 8:
        raise ValidationException(
            {"password": ["The password must be at least 8 characters."]}
        )
    secret = Config.get("app.key", "")
    user_id = verify_password_reset_token(data.token, secret)
    user = await User.find(user_id) if user_id is not None else None
    if user is None:
        raise ValidationException(
            {"token": ["This password reset token is invalid or has expired."]}
        )
    user.password = (
        data.password
    )  # the User model's `hashed` cast argon2-hashes on assignment
    await user.save()
    return MessageOut(message="Password has been reset.")
