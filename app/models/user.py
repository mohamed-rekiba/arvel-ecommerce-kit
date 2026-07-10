"""The User model."""

from datetime import datetime
from typing import Any, ClassVar

from arvel import Model
from arvel.auth import Authenticatable, HasRoles
from arvel.media import HasMedia, MediaConversion
from arvel.notifications import Notifiable

from app.enums import UserRole
from app.models.media import AppMedia

AVATAR = "avatar"  # single-image media collection


class User(HasMedia, Authenticatable, HasRoles, Notifiable, Model):
    __table_name__ = "users"
    __media_model__ = (
        AppMedia  # avatars expose serving_url() (media.md → extending Media)
    )
    __fields__: ClassVar[dict[str, type]] = {
        "name": str,
        "email": str,
        "email_verified_at": datetime,
        "password": str,
        "phone": str,
        "role": str,
        "locale": str,
    }
    __fillable__: ClassVar[list[str]] = [
        "name",
        "email",
        "password",
        "phone",
        "role",
        "locale",
    ]
    __hidden__: ClassVar[list[str]] = ["password"]
    __casts__: ClassVar[dict[str, Any]] = {
        "email_verified_at": "datetime",
        "password": "hashed",  # nosec B105
        "phone": "encrypted",  # PII — ciphertext at rest, transparent in the app
        "role": UserRole,
    }

    def register_media_conversions(self) -> list[MediaConversion]:
        """Avatar derivatives — profile (128) and chip (48) sizes, WEBP like the catalog."""
        return [
            MediaConversion("profile", width=128, height=128, fmt="WEBP"),
            MediaConversion("chip", width=48, height=48, fmt="WEBP"),
        ]

    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN
