"""Email-verification mail — the signed, expiring verification link (ShouldQueue). Localized to
the recipient's locale; rendered through the framework's themed markdown."""

from arvel.events import ShouldQueue
from arvel.mail import Mailable
from arvel.support.facades import Config

from app.i18n import trans_in


class VerifyEmail(Mailable, ShouldQueue):
    def __init__(self, user_id: int, token: str, locale: str = "en") -> None:
        super().__init__()
        self.user_id = user_id
        self.token = token
        self.locale = locale

    def build(self) -> "VerifyEmail":
        frontend = str(
            Config.get("app.frontend_url") or "http://localhost:5173"
        ).rstrip("/")
        link = f"{frontend}/verify-email?id={self.user_id}&token={self.token}"
        self.subject(trans_in(self.locale, "shop.mail.verify.subject"))
        self.markdown(
            f"# {trans_in(self.locale, 'shop.mail.verify.title')}\n\n"
            f"[button: {trans_in(self.locale, 'shop.mail.verify.action')}]({link})\n\n"
            f"{trans_in(self.locale, 'shop.mail.verify.expires')}\n"
        )
        return self
