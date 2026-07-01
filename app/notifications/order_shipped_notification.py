"""OrderShippedNotification — fans out over the mail + database channels (Laravel Notification).

When an order transitions to SHIPPED, the customer gets an email AND a stored (database-channel)
notification that surfaces in their account. Exercises arvel's notification system: Notification + the
Notifiable user + the DatabaseNotification store.
"""

from typing import Any

from arvel.notifications import Notification

from app.mail.order_shipped import OrderShipped


class OrderShippedNotification(Notification):
    def __init__(self, order_id: int, total_cents: int) -> None:
        self.order_id = order_id
        self.total_cents = total_cents

    def via(self, notifiable: Any) -> list[str]:
        return ["mail", "database"]

    def to_mail(self, notifiable: Any) -> OrderShipped:
        return OrderShipped(self.order_id)

    def to_array(self, notifiable: Any) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "total_cents": self.total_cents,
            "message": f"Your order #{self.order_id} has shipped.",
        }
