"""Email-verification mail — the signed, expiring verification link (ShouldQueue)."""

from arvel.events import ShouldQueue
from arvel.mail import Mailable
from arvel.support.facades import Config


class VerifyEmail(Mailable, ShouldQueue):
    def __init__(self, user_id: int, token: str) -> None:
        super().__init__()
        self.user_id = user_id
        self.token = token

    def build(self) -> "VerifyEmail":
        frontend = str(
            Config.get("app.frontend_url") or "http://localhost:5173"
        ).rstrip("/")
        link = f"{frontend}/verify-email?token={self.token}"
        self.subject("Verify your email address")
        self.html(
            "<h1>Almost there</h1>"
            f'<p><a href="{link}">Verify your email address</a> — this link expires in 24 hours.</p>'
        )
        return self
