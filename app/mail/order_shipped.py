"""The order-shipped email (the mailable) — the mail channel of OrderShippedNotification.
Localized to the RECIPIENT's stored locale via the kit lang catalogs (arvel.localization)."""

from arvel.mail import Mailable

from app.i18n import trans_in


class OrderShipped(Mailable):
    def __init__(
        self, order_id: int, tracking_number: str | None = None, locale: str = "en"
    ) -> None:
        super().__init__()
        self.order_id = order_id
        self.tracking_number = tracking_number
        self.locale = locale

    def build(self) -> "OrderShipped":
        self.subject(
            trans_in(self.locale, "shop.mail.shipped.subject", order=self.order_id)
        )
        title = trans_in(self.locale, "shop.mail.shipped.title")
        body = trans_in(self.locale, "shop.mail.shipped.body", order=self.order_id)
        md = f"# {title}\n\n{body}\n"
        if self.tracking_number:
            tracking = trans_in(
                self.locale, "shop.mail.shipped.tracking", tracking=self.tracking_number
            )
            md += f"\n{tracking}\n"
        self.markdown(md)
        return self
