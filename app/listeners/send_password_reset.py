"""Send the password-reset email when the broker fires ``PasswordResetRequested``.

The broker (``forgot_password``) only stores a hashed token and dispatches this event with the
plaintext token; delivering the link is the app's job, wired here so the broker stays transport-agnostic.
"""

from __future__ import annotations

from arvel.auth.password_reset import PasswordResetRequested
from arvel.support.facades import Mail

from app.mail.password_reset import PasswordReset
from app.models.user import User


async def send_password_reset(event: PasswordResetRequested) -> None:
    # the broker only carries email+token; render in the account's stored locale
    user = await User.where("email", event.email).first()
    locale = str(getattr(user, "locale", None) or "en")
    await Mail.to(event.email).send(PasswordReset(event.email, event.token, locale))
