"""Back-in-stock email — links straight to the product page (themed markdown button)."""

from arvel.mail import Mailable
from arvel.support.facades import Config

from app.i18n import trans_in


class BackInStock(Mailable):
    def __init__(
        self,
        product_name: str,
        product_slug: str,
        variant_name: str,
        locale: str = "en",
    ) -> None:
        super().__init__()
        self.product_name = product_name
        self.product_slug = product_slug
        self.variant_name = variant_name
        self.locale = locale

    def build(self) -> "BackInStock":
        frontend = str(
            Config.get("app.frontend_url") or "http://localhost:5173"
        ).rstrip("/")
        link = f"{frontend}/products/{self.product_slug}"
        self.subject(
            trans_in(
                self.locale,
                "shop.mail.back_in_stock.subject",
                product=self.product_name,
            )
        )
        title = trans_in(self.locale, "shop.mail.back_in_stock.title")
        body = trans_in(
            self.locale,
            "shop.mail.back_in_stock.body",
            product=f"{self.product_name} ({self.variant_name})",
        )
        self.markdown(f"# {title}\n\n{body}\n\n[button: {title}]({link})\n")
        return self
