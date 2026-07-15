"""Send the password-reset email when the broker fires ``PasswordResetRequested``.

The broker (``forgot_password``) only stores a hashed token and dispatches this event with the
plaintext token; delivering the link is the app's job. Auto-discovered from app/listeners/ — bound
to PasswordResetRequested by the handle type hint (arvel core dispatches it as a class event).
"""

from __future__ import annotations

from arvel.auth.password_reset import PasswordResetRequested
from arvel.support.facades import Mail

from app.mail.password_reset import PasswordReset
from app.models.user import User


class SendPasswordReset:
    async def handle(self, event: PasswordResetRequested) -> None:
        # the broker only carries email+token; render in the account's stored locale
        user = await User.where("email", event.email).first()
        locale = str(getattr(user, "mail_locale", None) or "en")
        await Mail.to(event.email).send(PasswordReset(event.email, event.token, locale))
