"""Password-reset email — carries the signed, expiring reset link (ShouldQueue: auth mail rides
the worker like every other mail). Localized to the recipient's locale; rendered through the
framework's themed markdown (styled button), not hand-built HTML."""

from arvel.events import ShouldQueue
from arvel.mail import Mailable
from arvel.support.facades import Config

from app.i18n import trans_in


class PasswordReset(Mailable, ShouldQueue):
    def __init__(self, email: str, token: str, locale: str = "en") -> None:
        super().__init__()
        self.email = email
        self.token = token
        self.locale = locale

    def build(self) -> "PasswordReset":
        frontend = str(
            Config.get("app.frontend_url") or "http://localhost:5173"
        ).rstrip("/")
        link = f"{frontend}/reset-password?token={self.token}&email={self.email}"
        self.subject(trans_in(self.locale, "shop.mail.reset.subject"))
        self.markdown(
            f"# {trans_in(self.locale, 'shop.mail.reset.title')}\n\n"
            f"[button: {trans_in(self.locale, 'shop.mail.reset.action')}]({link})\n\n"
            f"{trans_in(self.locale, 'shop.mail.reset.expires')}\n\n"
            f"{trans_in(self.locale, 'shop.mail.reset.ignore')}\n"
        )
        return self
