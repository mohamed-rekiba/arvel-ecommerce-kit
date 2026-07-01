"""The order-shipped email (Laravel Mailable) — the mail channel of OrderShippedNotification."""

from arvel.mail import Mailable


class OrderShipped(Mailable):
    def __init__(self, order_id: int) -> None:
        super().__init__()
        self.order_id = order_id

    def build(self) -> "OrderShipped":
        self.subject(f"Your order #{self.order_id} has shipped")
        self.html(
            f"<h1>On its way!</h1>"
            f"<p>Order <strong>#{self.order_id}</strong> has shipped and is en route to you.</p>"
        )
        return self
