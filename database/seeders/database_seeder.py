"""The root database seeder — run with ``arvel db:seed``."""

from arvel.database import Seeder

from app.services.product_image_service import ProductImageService
from database.factories.category_factory import CategoryFactory
from database.factories.product_factory import ProductFactory
from database.factories.product_variant_factory import ProductVariantFactory
from database.factories.user_factory import UserFactory

# Lorem Picsum — real photos, deterministic per seed, no API key. Each product gets a small gallery,
# downloaded through the arvel Http client and stored via the media library (with conversions).
_IMAGE_URL = "https://picsum.photos/seed/{seed}/800/1000"
_GALLERY_SIZE = 2


class DatabaseSeeder(Seeder):
    async def run(self) -> None:
        images = ProductImageService()
        await UserFactory().create(name="Test User", email="test@example.com")
        # a small catalog: 3 categories, each with a few products + variants + a real image gallery
        for _ in range(3):
            category = await CategoryFactory().create()
            for _ in range(4):
                product = await ProductFactory().create(category_id=category.id)
                for _ in range(2):
                    await ProductVariantFactory().create(product_id=product.id)
                for n in range(_GALLERY_SIZE):
                    url = _IMAGE_URL.format(seed=f"{product.slug}-{n}")
                    await images.download_and_attach(product, url, file_name=f"{product.slug}-{n}.jpg")
