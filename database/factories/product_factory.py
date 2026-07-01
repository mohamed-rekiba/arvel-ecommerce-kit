"""Product factory."""

from typing import Any

from arvel.database import Factory
from arvel.support import Str

from app.enums import ProductStatus
from app.models.product import Product


class ProductFactory(Factory[Product]):
    model = Product

    def definition(self) -> dict[str, Any]:
        name = self.faker.unique.catch_phrase()
        return {
            "category_id": None,  # set explicitly or via a state when seeding
            "translations": {
                "en": {"name": name, "description": self.faker.sentence()}
            },
            "slug": Str.slug(f"{name}-{self.faker.unique.random_int(1, 1_000_000)}"),
            "price_cents": self.faker.random_int(500, 50_000),
            "currency": "USD",
            "status": ProductStatus.ACTIVE,
            "published": True,
        }
