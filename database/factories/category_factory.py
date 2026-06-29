"""Category factory."""

from typing import Any

from arvel.database import Factory
from arvel.support import Str

from app.models.category import Category


class CategoryFactory(Factory[Category]):
    model = Category

    def definition(self) -> dict[str, Any]:
        name = self.faker.unique.word().title()
        return {
            "name": name,
            "slug": Str.slug(f"{name}-{self.faker.unique.random_int(1, 1_000_000)}"),
            "parent_id": None,
        }
