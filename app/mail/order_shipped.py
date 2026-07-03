"""The order-shipped email (Laravel Mailable) — the mail channel of OrderShippedNotification.
Localized to the RECIPIENT's stored locale via the kit lang catalogs (arvel.localization)."""

from arvel.mail import Mailable

from app.i18n import trans_in


class OrderShipped(Mailable):
    def __init__(self, order_id: int, locale: str = "en") -> None:
        super().__init__()
        self.order_id = order_id
        self.locale = locale

    def build(self) -> "OrderShipped":
        self.subject(
            trans_in(self.locale, "shop.mail.shipped.subject", order=self.order_id)
        )
        title = trans_in(self.locale, "shop.mail.shipped.title")
        body = trans_in(self.locale, "shop.mail.shipped.body", order=self.order_id)
        self.html(f"<h1>{title}</h1><p>{body}</p>")
        return self
