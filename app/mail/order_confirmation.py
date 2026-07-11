"""The order-confirmation email (a mailable), localized to the buyer's request locale.

``ShouldQueue``: checkout must never wait on — or 500 from — SMTP; delivery rides the worker
(and the failed-jobs rail) like every other order-lifecycle mail.
"""

from arvel.events import ShouldQueue
from arvel.mail import Mailable
from arvel.support import Money

from app.i18n import trans_in


class OrderConfirmation(Mailable, ShouldQueue):
    def __init__(
        self,
        order_id: int,
        total_cents: int,
        currency: str = "USD",
        locale: str = "en",
    ) -> None:
        super().__init__()
        self.order_id = order_id
        self.total_cents = total_cents
        self.currency = currency
        self.locale = locale

    def build(self) -> "OrderConfirmation":
        # locale-aware, currency-correct ($19.99 / 19,99 $US) — never a hand-rolled f"${...}"
        total = Money(self.total_cents, self.currency).format(self.locale)
        self.subject(
            trans_in(self.locale, "shop.mail.confirmed.subject", order=self.order_id)
        )
        title = trans_in(self.locale, "shop.mail.confirmed.title")
        body = trans_in(
            self.locale, "shop.mail.confirmed.body", order=self.order_id, total=total
        )
        self.markdown(f"# {title}\n\n{body}\n")
        return self
