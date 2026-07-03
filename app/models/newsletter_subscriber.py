"""A newsletter signup — one row per email (idempotent subscribe)."""

from typing import ClassVar

from arvel import Model


class NewsletterSubscriber(Model):
    __table_name__ = "newsletter_subscribers"
    __fields__: ClassVar[dict[str, type]] = {"email": str, "locale": str}
    __fillable__: ClassVar[list[str]] = ["email", "locale"]
