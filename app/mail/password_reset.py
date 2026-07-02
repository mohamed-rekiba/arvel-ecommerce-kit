"""Password-reset email — carries the signed, expiring reset link (ShouldQueue: auth mail rides
the worker like every other mail)."""

from arvel.events import ShouldQueue
from arvel.mail import Mailable
from arvel.support.facades import Config


class PasswordReset(Mailable, ShouldQueue):
    def __init__(self, email: str, token: str) -> None:
        super().__init__()
        self.email = email
        self.token = token

    def build(self) -> "PasswordReset":
        frontend = str(
            Config.get("app.frontend_url") or "http://localhost:5173"
        ).rstrip("/")
        link = f"{frontend}/reset-password?token={self.token}&email={self.email}"
        self.subject("Reset your Arvel Shop password")
        self.html(
            "<h1>Reset your password</h1>"
            f'<p><a href="{link}">Choose a new password</a> — this link expires in 1 hour.</p>'
            "<p>If you didn't ask for this, you can ignore it.</p>"
        )
        return self
