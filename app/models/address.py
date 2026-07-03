"""The Address model — one saved shipping address in a customer's address book."""

from typing import Any, ClassVar

from arvel import Model


class Address(Model):
    __table_name__ = "addresses"
    __fields__: ClassVar[dict[str, type]] = {
        "user_id": int,
        "label": str,
        "name": str,
        "line1": str,
        "line2": str,
        "city": str,
        "postal_code": str,
        "country": str,
        "phone": str,
        "is_default": bool,
    }
    __fillable__: ClassVar[list[str]] = [
        "user_id",
        "label",
        "name",
        "line1",
        "line2",
        "city",
        "postal_code",
        "country",
        "phone",
        "is_default",
    ]
    __casts__: ClassVar[dict[str, Any]] = {"is_default": bool}

    def user(self) -> Any:
        from app.models.user import User

        return self.belongs_to(User)
