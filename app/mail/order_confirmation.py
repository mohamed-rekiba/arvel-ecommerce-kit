"""The order-confirmation email (Laravel Mailable).

``ShouldQueue``: checkout must never wait on — or 500 from — SMTP; delivery rides the worker
(and the failed-jobs rail) like every other order-lifecycle mail.
"""

from arvel.events import ShouldQueue
from arvel.mail import Mailable


class OrderConfirmation(Mailable, ShouldQueue):
    def __init__(self, order_id: int, total_cents: int) -> None:
        super().__init__()
        self.order_id = order_id
        self.total_cents = total_cents

    def build(self) -> "OrderConfirmation":
        total = f"${self.total_cents / 100:.2f}"
        self.subject(f"Your order #{self.order_id} is confirmed")
        self.html(
            f"<h1>Thanks for your order!</h1>"
            f"<p>Order <strong>#{self.order_id}</strong> totalling {total} has been received.</p>"
        )
        return self
