"""OrderShippedNotification — queued fan-out over the database + mail channels.

``ShouldQueue`` puts delivery on the worker (one queued job PER channel — the framework's
per-channel queueing), so the SHIPPED transition commits without waiting on SMTP, an SMTP outage
can only fail the mail job (retried → failed-jobs rail), and the database channel is stored by its
own job regardless. ``via()`` lists the database channel first: the stored notification is the
source of truth the account UI reads; mail is the best-effort courtesy copy.
"""

from typing import Any

from arvel.events import ShouldQueue
from arvel.notifications import Notification

from app.i18n import trans_in
from app.mail.order_shipped import OrderShipped


class OrderShippedNotification(Notification, ShouldQueue):
    def __init__(self, order_id: int, tracking_number: str | None = None) -> None:
        self.order_id = order_id
        self.tracking_number = tracking_number

    def via(self, notifiable: Any) -> list[str]:
        return ["database", "mail"]

    def to_mail(self, notifiable: Any) -> OrderShipped:
        return OrderShipped(
            self.order_id,
            self.tracking_number,
            locale=str(getattr(notifiable, "mail_locale", None) or "en"),
        )

    def to_array(self, notifiable: Any) -> dict[str, Any]:
        locale = str(getattr(notifiable, "mail_locale", None) or "en")
        return {
            "order_id": self.order_id,
            "tracking_number": self.tracking_number,
            "message": trans_in(locale, "shop.notif.shipped", order=self.order_id),
        }
