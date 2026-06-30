"""User factory — generates fake users for tests and seeders."""

from typing import Any

from arvel.database import Factory

from app.enums import UserRole
from app.models.user import User


class UserFactory(Factory[User]):
    model = User

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.faker.name(),
            "email": self.faker.unique.email(),
            "password": "password",  # the User model's `hashed` cast argon2-hashes this on save
            "role": UserRole.CUSTOMER,
        }

    def admin(self) -> Factory[User]:
        """A factory state for an admin user (Laravel factory state)."""
        return self.state({"role": UserRole.ADMIN})
