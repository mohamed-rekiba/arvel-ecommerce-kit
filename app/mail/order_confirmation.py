"""The order-confirmation email (a mailable), localized to the buyer's request locale.

``ShouldQueue``: checkout must never wait on — or 500 from — SMTP; delivery rides the worker
(and the failed-jobs rail) like every other order-lifecycle mail.
"""

from arvel.events import ShouldQueue
from arvel.mail import Mailable

from app.i18n import trans_in


class OrderConfirmation(Mailable, ShouldQueue):
    def __init__(self, order_id: int, total_cents: int, locale: str = "en") -> None:
        super().__init__()
        self.order_id = order_id
        self.total_cents = total_cents
        self.locale = locale

    def build(self) -> "OrderConfirmation":
        total = f"${self.total_cents / 100:.2f}"
        self.subject(
            trans_in(self.locale, "shop.mail.confirmed.subject", order=self.order_id)
        )
        title = trans_in(self.locale, "shop.mail.confirmed.title")
        body = trans_in(
            self.locale, "shop.mail.confirmed.body", order=self.order_id, total=total
        )
        self.html(f"<h1>{title}</h1><p>{body}</p>")
        return self
