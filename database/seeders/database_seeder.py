"""The root database seeder — run with ``arvel db:seed``.

Seeds a realistic electronics-boutique catalog: several published vendors (brands), a category tree,
and ~20 products with varied prices and **real, category-matched gallery images** (keyword photos from
loremflickr, fetched via the arvel Http client and stored through the media library with thumb/preview
conversions). Also keeps the retrievability edge cases — an empty category, an unpublished category
branch, an unpublished vendor, and a draft product — so the retrievable_* views can be seen filtering.
"""

import asyncio

from arvel.database import Seeder

from app.models.category import Category
from app.models.product import Product
from app.models.vendor import Vendor
from app.services.catalog_visibility_service import CatalogVisibilityService
from app.services.product_image_service import ProductImageService
from database.factories.product_variant_factory import ProductVariantFactory
from database.factories.user_factory import UserFactory
from database.seeders.roles_permissions_seeder import RolesPermissionsSeeder

# curated, clean PRODUCT photos (Unsplash) per product type — a real studio shot of the actual item,
# not a keyword-tagged random photo. Fetched via the Http client + stored through the media library.
_UNSPLASH = {
    "headphones": "1505740420928-5e560c06d30e",
    "earbuds": "1590658268037-6bf12165a8df",
    "speaker": "1608043152269-423dbba4e7e1",
    "smartphone": "1511707171634-5f897ff02aa9",
    "phone": "1511707171634-5f897ff02aa9",
    "laptop": "1496181133206-80ce9b88a853",
    "monitor": "1527443224154-c4a3942d3acf",
    "smartwatch": "1523275335684-37898b6baf30",
    "camera": "1502920917128-1aa500764cbd",
    "keyboard": "1587829741301-dc798b83add3",
    "mouse": "1527814050087-3793815479db",
    "charger": "1588872657578-7efd1f1555ed",
    "bag": "1553062407-98eeb64c6a62",
}
# two crops of the shot → a small gallery (test_product_images asserts the first product has 2 images)
_IMG_PARAMS = [
    "?w=900&h=1125&fit=crop&q=80",
    "?w=900&h=1125&fit=crop&crop=entropy&q=80",
]
_GALLERY_SIZE = 2


class DatabaseSeeder(Seeder):
    async def run(self) -> None:
        images = ProductImageService()
        await (
            RolesPermissionsSeeder().run()
        )  # permissions, roles, one back-office user per role
        await UserFactory().create(name="Test User", email="test@example.com")

        # --- vendors (brands) -------------------------------------------------
        vendors: dict[str, Vendor] = {}
        for name, slug in [
            ("Nordic Audio", "nordic-audio"),
            ("Lumen", "lumen"),
            ("Cobalt", "cobalt"),
            ("Aperture", "aperture"),
            ("Verge", "verge"),
        ]:
            vendors[slug] = await Vendor.create(name=name, slug=slug, published=True)
        await Vendor.create(
            name="Shady Imports", slug="shady", published=False
        )  # unpublished vendor

        # --- category tree (parents + published children) ---------------------
        audio = await self._cat("Audio", "audio", fr="Audio")
        headphones = await self._cat("Headphones", "headphones", parent=audio.id)
        earbuds = await self._cat("Earbuds", "earbuds", parent=audio.id)
        speakers = await self._cat("Speakers", "speakers", parent=audio.id)
        phones = await self._cat("Phones", "phones", fr="Téléphones")
        computing = await self._cat("Computing", "computing")
        laptops = await self._cat("Laptops", "laptops", parent=computing.id)
        monitors = await self._cat("Monitors", "monitors", parent=computing.id)
        wearables = await self._cat("Wearables", "wearables")
        cameras = await self._cat("Cameras", "cameras")
        accessories = await self._cat("Accessories", "accessories")

        # --- catalog: (category, vendor, price_cents, image keyword, name) ----
        catalog = [
            (
                headphones,
                "nordic-audio",
                29900,
                "headphones",
                "Aurora Over-Ear Headphones",
            ),
            (
                headphones,
                "nordic-audio",
                34900,
                "headphones,studio",
                "Eclipse Studio Headphones",
            ),
            (earbuds, "nordic-audio", 14900, "earbuds", "Pulse Wireless Earbuds"),
            (earbuds, "nordic-audio", 9900, "earbuds,wireless", "Drift Earbuds"),
            (speakers, "nordic-audio", 24900, "speaker", "Resonate Bookshelf Speaker"),
            (
                speakers,
                "nordic-audio",
                12900,
                "speaker,bluetooth",
                "Nomad Portable Speaker",
            ),
            (phones, "lumen", 89900, "smartphone", "Nimbus 5G Phone"),
            (phones, "lumen", 79900, "smartphone,phone", "Aurora Phone"),
            (phones, "lumen", 59900, "phone", "Vertex Mini"),
            (laptops, "cobalt", 149900, "laptop", "Photon 14 Laptop"),
            (laptops, "cobalt", 219900, "laptop,computer", "Photon 16 Pro"),
            (monitors, "lumen", 64900, "monitor", "Lumen 27 4K Monitor"),
            (monitors, "lumen", 99900, "monitor,screen", "Lumen 32 Ultrawide"),
            (wearables, "verge", 39900, "smartwatch", "Orbit Smartwatch"),
            (wearables, "verge", 29900, "smartwatch,sport", "Orbit Sport"),
            (cameras, "aperture", 129900, "camera", "Aperture X100 Camera"),
            (cameras, "aperture", 79900, "camera,lens", "Field Zoom Lens"),
            (
                accessories,
                "cobalt",
                16900,
                "keyboard,mechanical",
                "Cobalt Mechanical Keyboard",
            ),
            (accessories, "cobalt", 7900, "mouse,computer", "Cobalt Wireless Mouse"),
            (accessories, "verge", 5900, "charger,dock", "Verge Charging Dock"),
            (accessories, "verge", 8900, "bag", "Verge Leather Sleeve"),
        ]
        for category, vendor_slug, price, keyword, name in catalog:
            product = await self._product(
                name,
                category.id,
                vendors[vendor_slug].id,
                price_cents=price,
                published=True,
            )
            for _ in range(2):
                await ProductVariantFactory().create(product_id=product.id)
            photo_id = _UNSPLASH.get(keyword.split(",")[0])
            for n in range(_GALLERY_SIZE):
                if not photo_id:
                    break
                url = f"https://images.unsplash.com/photo-{photo_id}{_IMG_PARAMS[n % len(_IMG_PARAMS)]}"
                for _attempt in range(3):
                    if await images.download_and_attach(
                        product, url, file_name=f"{product.slug}-{n}.jpg"
                    ):
                        break
                    await asyncio.sleep(0.4)

        # --- retrievability edge cases (hidden; no galleries needed) ----------
        await self._cat("Gift Cards", "gift-cards")  # empty published category → hidden
        coming = await self._cat(
            "Coming Soon", "coming-soon", published=False
        )  # unpublished branch
        teasers = await self._cat("Teasers", "teasers", parent=coming.id)
        acme = vendors["nordic-audio"].id
        await self._product(
            "Secret Gadget", teasers.id, acme, price_cents=1999, published=True
        )
        await self._product(
            "Grey Market Phone", phones.id, 6, price_cents=1999, published=True
        )  # unpub vendor (id 6)
        await self._product(
            "Draft Phone", phones.id, acme, price_cents=1999, published=False
        )

        await CatalogVisibilityService().refresh()
        await (
            Product.make_all_searchable()
        )  # populate the search engine (Scout scout:import parity)

    @staticmethod
    async def _cat(
        name: str,
        slug: str,
        *,
        parent: int | None = None,
        published: bool = True,
        fr: str | None = None,
    ) -> Category:
        translations: dict[str, dict[str, str]] = {"en": {"name": name}}
        if fr:
            translations["fr"] = {"name": fr}
        return await Category.create(
            translations=translations, slug=slug, parent_id=parent, published=published
        )

    @staticmethod
    async def _product(
        name: str,
        category_id: int,
        vendor_id: int,
        *,
        price_cents: int,
        published: bool,
    ) -> Product:
        slug = name.lower().replace(" ", "-")
        return await Product.create(
            translations={
                "en": {
                    "name": name,
                    "description": f"{name} — considered design, built to last.",
                }
            },
            slug=slug,
            category_id=category_id,
            vendor_id=vendor_id,
            price_cents=price_cents,
            currency="USD",
            status="active" if published else "draft",
            published=published,
        )
