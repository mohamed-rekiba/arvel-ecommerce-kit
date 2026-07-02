"""Back-in-stock email — links straight to the product page."""

from arvel.mail import Mailable
from arvel.support.facades import Config


class BackInStock(Mailable):
    def __init__(self, product_name: str, product_slug: str, variant_name: str) -> None:
        super().__init__()
        self.product_name = product_name
        self.product_slug = product_slug
        self.variant_name = variant_name

    def build(self) -> "BackInStock":
        frontend = str(
            Config.get("app.frontend_url") or "http://localhost:5173"
        ).rstrip("/")
        link = f"{frontend}/products/{self.product_slug}"
        self.subject(f"Back in stock: {self.product_name}")
        self.html(
            f"<h1>{self.product_name} is back</h1>"
            f"<p>The {self.variant_name} variant you were waiting for is available again — "
            f'<a href="{link}">grab it before it goes</a>.</p>'
        )
        return self
