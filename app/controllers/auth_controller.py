"""Customer authentication — registration, login (token issue), logout (token revoke), and the
password-reset flow. Exercises arvel's auth (tokens + abilities + TokenGuard), hashing, request
validation, and the signed password-reset tokens.
"""

from typing import Any

from arvel import Schema, abort
from arvel.auth.flows import password_reset_token, verify_password_reset_token
from arvel.auth.tokens import TokenGuard, create_token
from arvel.support.facades import Config
from arvel.validation import Validator

from app.models.user import User

# Customer tokens are scoped to the "customer" ability (admins authenticate via OIDC, not here).
CUSTOMER_ABILITY = "customer"


class Registration(Schema):
    name: str
    email: str
    password: str


async def register(request, data: Registration) -> Any:
    """POST /api/register — validate, create the customer, issue a scoped token."""
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
        abort(422, validator.errors())
    if await User.where("email", data.email).first() is not None:
        abort(422, {"email": ["This email is already registered."]})
    user = await User.create(name=data.name, email=data.email, password=data.password)
    token, _ = await create_token(user, name="customer", abilities=[CUSTOMER_ABILITY])
    from arvel.http import Response

    return Response(content={"token": token}, status=201)


async def logout(request) -> Any:
    """POST /api/logout — revoke ONLY the current token (Sanctum currentAccessToken()->delete())."""
    token = await TokenGuard().token(request)
    if token is None:
        abort(401, "Unauthenticated")
    await token.delete()
    from arvel.http import Response

    return Response(content={"message": "Logged out."}, status=200)


async def forgot_password(request) -> Any:
    """POST /api/forgot-password — issue a signed reset token. Always 200 (non-enumerating); a real
    app emails the token rather than returning it."""
    data = await request.json()
    email = data.get("email", "")
    user = await User.where("email", email).first()
    payload: dict[str, Any] = {"message": "If that email exists, a reset link has been sent."}
    if user is not None:
        secret = Config.get("app.key", "")
        payload["reset_token"] = password_reset_token(user.id, secret)  # dev only — normally emailed
    from arvel.http import Response

    return Response(content=payload, status=200)


async def reset_password(request) -> Any:
    """POST /api/reset-password — verify the signed token, set the new (hashed) password."""
    data = await request.json()
    token = data.get("token", "")
    new_password = data.get("password", "")
    if len(new_password) < 8:
        abort(422, {"password": ["The password must be at least 8 characters."]})
    secret = Config.get("app.key", "")
    user_id = verify_password_reset_token(token, secret)
    if user_id is None:
        abort(422, {"token": ["This password reset token is invalid or has expired."]})
    user = await User.find(user_id)
    if user is None:
        abort(422, {"token": ["This password reset token is invalid or has expired."]})
    user.password = new_password  # the User model's `hashed` cast argon2-hashes on assignment
    await user.save()
    from arvel.http import Response

    return Response(content={"message": "Password has been reset."}, status=200)
