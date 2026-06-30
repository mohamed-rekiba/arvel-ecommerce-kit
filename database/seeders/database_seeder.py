"""The root database seeder — run with ``arvel db:seed``.

Seeds a catalog that exercises the retrievability rules: published products under a fully-published
category tree with a published vendor (these show in the storefront), plus deliberately-hidden cases —
an unpublished category branch, an unpublished vendor, a draft product, and an empty category — so the
retrievable_products / retrievable_categories views can be seen filtering. Refreshes the views at the end.
"""

from arvel.database import Seeder

from app.models.category import Category
from app.models.product import Product
from app.models.vendor import Vendor
from app.services.catalog_visibility_service import CatalogVisibilityService
from app.services.product_image_service import ProductImageService
from database.factories.product_variant_factory import ProductVariantFactory
from database.factories.user_factory import UserFactory

_IMAGE_URL = "https://picsum.photos/seed/{seed}/800/1000"
_GALLERY_SIZE = 2


class DatabaseSeeder(Seeder):
    async def run(self) -> None:
        images = ProductImageService()
        await UserFactory().create(name="Test User", email="test@example.com")

        acme = await Vendor.create(name="Acme Goods", slug="acme", published=True)
        await Vendor.create(name="Shady Imports", slug="shady", published=False)  # unpublished vendor

        # --- a published category tree (these branches are visible) ---
        electronics = await Category.create(name="Electronics", slug="electronics", published=True)
        phones = await Category.create(
            name="Phones", slug="phones", parent_id=electronics.id, published=True
        )
        laptops = await Category.create(
            name="Laptops", slug="laptops", parent_id=electronics.id, published=True
        )
        apparel = await Category.create(name="Apparel", slug="apparel", published=True)
        shirts = await Category.create(
            name="Shirts", slug="shirts", parent_id=apparel.id, published=True
        )
        # an empty published category — must be HIDDEN (no products in its subtree)
        await Category.create(name="Gift Cards", slug="gift-cards", published=True)
        # an unpublished branch — its (published) child + products must be HIDDEN
        coming = await Category.create(name="Coming Soon", slug="coming-soon", published=False)
        teasers = await Category.create(
            name="Teasers", slug="teasers", parent_id=coming.id, published=True
        )

        # --- retrievable products (published + Acme + published category) with real galleries ---
        catalog = {phones: ["Aurora Phone", "Nimbus Phone"], laptops: ["Photon Laptop"], shirts: ["Linen Shirt"]}
        for category, names in catalog.items():
            for name in names:
                product = await self._product(name, category.id, acme.id, published=True)
                for _ in range(2):
                    await ProductVariantFactory().create(product_id=product.id)
                for n in range(_GALLERY_SIZE):
                    url = _IMAGE_URL.format(seed=f"{product.slug}-{n}")
                    await images.download_and_attach(
                        product, url, file_name=f"{product.slug}-{n}.jpg"
                    )

        # --- deliberately hidden products (no galleries needed) ---
        await self._product("Secret Gadget", teasers.id, acme.id, published=True)  # unpublished ancestor
        await self._product("Grey Market Phone", phones.id, 2, published=True)  # unpublished vendor (id 2)
        await self._product("Draft Phone", phones.id, acme.id, published=False)  # not published

        await CatalogVisibilityService().refresh()

    @staticmethod
    async def _product(name: str, category_id: int, vendor_id: int, *, published: bool) -> Product:
        slug = name.lower().replace(" ", "-")
        return await Product.create(
            name=name,
            slug=slug,
            category_id=category_id,
            vendor_id=vendor_id,
            description=f"{name} — a quality item.",
            price_cents=1999,
            currency="USD",
            status="active" if published else "draft",
            published=published,
        )
