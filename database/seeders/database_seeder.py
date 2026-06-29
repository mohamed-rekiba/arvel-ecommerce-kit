"""The root database seeder — run with ``arvel db:seed``."""

from arvel.database import Seeder

from database.factories.category_factory import CategoryFactory
from database.factories.product_factory import ProductFactory
from database.factories.product_variant_factory import ProductVariantFactory
from database.factories.user_factory import UserFactory


class DatabaseSeeder(Seeder):
    async def run(self) -> None:
        await UserFactory().create(name="Test User", email="test@example.com")
        # a small catalog: 3 categories, each with a few products + variants
        for _ in range(3):
            category = await CategoryFactory().create()
            for _ in range(4):
                product = await ProductFactory().create(category_id=category.id)
                for _ in range(2):
                    await ProductVariantFactory().create(product_id=product.id)
