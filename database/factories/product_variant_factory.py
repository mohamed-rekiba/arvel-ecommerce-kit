"""ProductVariant factory."""

from typing import Any

from arvel.database import Factory

from app.models.product_variant import ProductVariant


class ProductVariantFactory(Factory[ProductVariant]):
    model = ProductVariant

    def definition(self) -> dict[str, Any]:
        return {
            "product_id": None,  # set explicitly when seeding
            "sku": self.faker.unique.bothify("SKU-#####-???").upper(),
            "name": self.faker.color_name(),
            "price_adjustment_cents": self.faker.random_int(0, 2_000),
            "stock": self.faker.random_int(0, 200),
        }
