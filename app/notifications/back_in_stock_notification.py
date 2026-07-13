"""BackInStockNotification — queued fan-out (database + mail) when a watched variant returns."""

from typing import Any

from arvel.events import ShouldQueue
from arvel.notifications import Notification
from arvel.queue.middleware import RateLimited

from app.i18n import trans_in
from app.mail.back_in_stock import BackInStock


class BackInStockNotification(Notification, ShouldQueue):
    def __init__(self, product_name: str, product_slug: str, variant_name: str) -> None:
        self.product_name = product_name
        self.product_slug = product_slug
        self.variant_name = variant_name

    def via(self, notifiable: Any) -> list[str]:
        return ["database", "mail"]

    def middleware(
        self, notifiable: Any = None, channels: list[str] | None = None
    ) -> list[Any]:
        """A flapping restock re-subscribes + re-fires per customer; without this a single eager
        customer could get spammed once per flap. Keyed on the recipient's id (not just the
        product/variant) so one customer hitting the limit never suppresses another's notification
        for the same variant — the key must include WHO, not just WHAT. Guard a vanished recipient
        (deleted between enqueue and the worker running this).

        Also folds in ``channels`` (the ONE channel THIS queued job carries — ``via()`` returns
        both ``database`` and ``mail``, so a single send pushes one job per channel and BOTH call
        this same method). Without the channel in the key, the mail job and the database job for
        the very SAME restock would share one counter and, at ``max_attempts=1``, only whichever
        ran first would ever deliver — even with no flapping at all. Each channel gets its own
        counter instead, so one restock still delivers to both."""
        if notifiable is None:
            return []
        from arvel.kernel import app

        # resolved fresh from the container, never stored on self — a live limiter can't survive
        # the queue's JSON serialization of the notification.
        limiter = app().make("limiter")
        channel = (channels or ["unknown"])[0]
        key = f"notif:back_in_stock:{notifiable.id}:{self.product_slug}:{self.variant_name}:{channel}"
        return [RateLimited(limiter, key=key, max_attempts=1, decay_seconds=300)]

    def to_mail(self, notifiable: Any) -> BackInStock:
        return BackInStock(
            self.product_name,
            self.product_slug,
            self.variant_name,
            locale=str(getattr(notifiable, "mail_locale", None) or "en"),
        )

    def to_array(self, notifiable: Any) -> dict[str, Any]:
        locale = str(getattr(notifiable, "mail_locale", None) or "en")
        return {
            "product_slug": self.product_slug,
            "message": trans_in(
                locale,
                "shop.notif.back_in_stock",
                product=f"{self.product_name} ({self.variant_name})",
            ),
        }
