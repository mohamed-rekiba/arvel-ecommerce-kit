"""The User model."""

from datetime import datetime
from typing import Any, ClassVar

from arvel import Model
from arvel.auth import Authenticatable

from app.enums import UserRole


class User(Authenticatable, Model):
    __table_name__ = "users"
    __fields__: ClassVar[dict[str, type]] = {
        "name": str,
        "email": str,
        "email_verified_at": datetime,
        "password": str,
        "role": str,
    }
    __fillable__: ClassVar[list[str]] = ["name", "email", "password", "role"]
    __hidden__: ClassVar[list[str]] = ["password"]
    __casts__: ClassVar[dict[str, Any]] = {
        "email_verified_at": "datetime",
        "password": "hashed",
        "role": UserRole,
    }

    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN
