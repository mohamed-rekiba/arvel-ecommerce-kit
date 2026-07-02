"""BackInStockNotification — queued fan-out (database + mail) when a watched variant returns."""

from typing import Any

from arvel.events import ShouldQueue
from arvel.notifications import Notification

from app.mail.back_in_stock import BackInStock


class BackInStockNotification(Notification, ShouldQueue):
    def __init__(self, product_name: str, product_slug: str, variant_name: str) -> None:
        self.product_name = product_name
        self.product_slug = product_slug
        self.variant_name = variant_name

    def via(self, notifiable: Any) -> list[str]:
        return ["database", "mail"]

    def to_mail(self, notifiable: Any) -> BackInStock:
        return BackInStock(self.product_name, self.product_slug, self.variant_name)

    def to_array(self, notifiable: Any) -> dict[str, Any]:
        return {
            "product_slug": self.product_slug,
            "message": f"{self.product_name} ({self.variant_name}) is back in stock!",
        }
