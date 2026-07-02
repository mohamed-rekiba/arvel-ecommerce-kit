"""The root database seeder — run with ``arvel db:seed``.

Seeds a realistic electronics-boutique catalog: several published vendors (brands), a category tree,
and ~20 products with varied prices and **real, category-matched gallery images** (keyword photos from
loremflickr, fetched via the arvel Http client and stored through the media library with thumb/preview
conversions). Also keeps the retrievability edge cases — an empty category, an unpublished category
branch, an unpublished vendor, and a draft product — so the retrievable_* views can be seen filtering.
"""

import asyncio

from arvel.database import Seeder

from app.enums import CouponType
from app.models.banner import HERO, Banner
from app.models.category import Category
from app.models.coupon import Coupon
from app.models.deal import Deal
from app.models.product import Product
from app.models.vendor import Vendor
from arvel.dates import Date
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
        audio = await self._cat("Audio", "audio", fr="Audio", ar="صوتيات")
        headphones = await self._cat(
            "Headphones", "headphones", parent=audio.id, fr="Casques", ar="سماعات رأس"
        )
        earbuds = await self._cat(
            "Earbuds", "earbuds", parent=audio.id, fr="Écouteurs", ar="سماعات أذن"
        )
        speakers = await self._cat(
            "Speakers", "speakers", parent=audio.id, fr="Enceintes", ar="مكبرات صوت"
        )
        phones = await self._cat("Phones", "phones", fr="Téléphones", ar="هواتف")
        computing = await self._cat(
            "Computing", "computing", fr="Informatique", ar="حواسيب"
        )
        laptops = await self._cat(
            "Laptops",
            "laptops",
            parent=computing.id,
            fr="Ordinateurs portables",
            ar="حواسيب محمولة",
        )
        monitors = await self._cat(
            "Monitors", "monitors", parent=computing.id, fr="Écrans", ar="شاشات"
        )
        wearables = await self._cat(
            "Wearables", "wearables", fr="Objets connectés", ar="أجهزة قابلة للارتداء"
        )
        cameras = await self._cat(
            "Cameras", "cameras", fr="Appareils photo", ar="كاميرات"
        )
        accessories = await self._cat(
            "Accessories", "accessories", fr="Accessoires", ar="إكسسوارات"
        )

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
        fr_names = {
            "Eclipse Studio Headphones": "Casque Studio Eclipse",
            "Aurora Over-Ear Headphones": "Casque circum-aural Aurora",
            "Pulse Wireless Earbuds": "Écouteurs sans fil Pulse",
            "Drift Earbuds": "Écouteurs Drift",
            "Resonate Bookshelf Speaker": "Enceinte de bibliothèque Resonate",
            "Nomad Portable Speaker": "Enceinte portable Nomad",
            "Nimbus 5G Phone": "Téléphone Nimbus 5G",
            "Aurora Phone": "Téléphone Aurora",
            "Vertex Mini": "Vertex Mini",
            "Photon 14 Laptop": "Ordinateur portable Photon 14",
            "Photon 16 Pro": "Photon 16 Pro",
            "Lumen 27 4K Monitor": "Écran 4K Lumen 27",
            "Lumen 32 Ultrawide": "Écran ultra-large Lumen 32",
            "Orbit Smartwatch": "Montre connectée Orbit",
            "Orbit Sport": "Orbit Sport",
            "Aperture X100 Camera": "Appareil photo Aperture X100",
            "Field Zoom Lens": "Objectif zoom Field",
            "Cobalt Mechanical Keyboard": "Clavier mécanique Cobalt",
            "Cobalt Wireless Mouse": "Souris sans fil Cobalt",
            "Verge Charging Dock": "Station de charge Verge",
            "Verge Leather Sleeve": "Housse en cuir Verge",
        }
        ar_names = {
            "Eclipse Studio Headphones": "سماعات استوديو إكليبس",
            "Aurora Over-Ear Headphones": "سماعات أورورا فوق الأذن",
            "Pulse Wireless Earbuds": "سماعات بالس اللاسلكية",
            "Drift Earbuds": "سماعات دريفت",
            "Resonate Bookshelf Speaker": "مكبر صوت ريزونيت المكتبي",
            "Nomad Portable Speaker": "مكبر صوت نوماد المحمول",
            "Nimbus 5G Phone": "هاتف نيمبوس 5G",
            "Aurora Phone": "هاتف أورورا",
            "Vertex Mini": "فيرتكس ميني",
            "Photon 14 Laptop": "حاسوب فوتون 14 المحمول",
            "Photon 16 Pro": "فوتون 16 برو",
            "Lumen 27 4K Monitor": "شاشة لومن 27 بدقة 4K",
            "Lumen 32 Ultrawide": "شاشة لومن 32 العريضة",
            "Orbit Smartwatch": "ساعة أوربِت الذكية",
            "Orbit Sport": "أوربِت سبورت",
            "Aperture X100 Camera": "كاميرا أبرتشر X100",
            "Field Zoom Lens": "عدسة فيلد للتقريب",
            "Cobalt Mechanical Keyboard": "لوحة مفاتيح كوبالت الميكانيكية",
            "Cobalt Wireless Mouse": "فأرة كوبالت اللاسلكية",
            "Verge Charging Dock": "قاعدة شحن فيرج",
            "Verge Leather Sleeve": "حافظة جلدية من فيرج",
        }
        featured_names = {
            "Aurora Phone",
            "Eclipse Studio Headphones",
            "Photon 14 Laptop",
            "Orbit Smartwatch",
            "Lumen 27 4K Monitor",
            "Aperture X100 Camera",
        }
        products_by_name: dict[str, Product] = {}
        for category, vendor_slug, price, keyword, name in catalog:
            product = await self._product(
                name,
                category.id,
                vendors[vendor_slug].id,
                price_cents=price,
                published=True,
                fr=fr_names.get(name),
                ar=ar_names.get(name),
            )
            products_by_name[name] = product
            if name in featured_names:
                product.featured = True
                await product.save()
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

        # --- deals of the day (2 live + 1 expired for realism) ---------------
        now = Date.now()
        for name, pct, hours in (
            ("Aurora Phone", 25, 23),
            ("Photon 14 Laptop", 20, 10),
        ):
            target = products_by_name[name]
            await Deal.create(
                product_id=target.id,
                percent_off=pct,
                starts_at=now.subtract(hours=2),
                ends_at=now.add(hours=hours),
                active=True,
            )
        await Deal.create(
            product_id=products_by_name["Drift Earbuds"].id,
            percent_off=30,
            starts_at=now.subtract(days=6),
            ends_at=now.subtract(days=1),
            active=True,
        )

        # --- the announced welcome coupon -------------------------------------
        await Coupon.create(
            code="WELCOME10",
            type=CouponType.PERCENT,
            value=10,
            uses=0,
            active=True,
            announce=True,
        )

        # --- hero banners (admin-managed carousel) -----------------------------
        banners = [
            (
                {
                    "en": {"title": "Premium audio, quietly considered", "subtitle": "Studio headphones and speakers chosen for how they feel.", "chip": "New arrival", "cta_label": "Shop now"},
                    "fr": {"title": "L'audio haut de gamme, pensé en toute discrétion", "subtitle": "Casques studio et enceintes choisis pour leurs sensations.", "chip": "Nouveauté", "cta_label": "Acheter"},
                    "ar": {"title": "صوتيات فاخرة بتصميم هادئ", "subtitle": "سماعات استوديو ومكبرات صوت اخترناها لإحساسها.", "chip": "وصل حديثًا", "cta_label": "تسوق الآن"},
                },
                "/catalog?category=audio",
                0,
                "1505740420928-5e560c06d30e",
            ),
            (
                {
                    "en": {"title": "Deals of the day", "subtitle": "Timed flash sales on the gear you already wanted.", "chip": "Up to 25% off", "cta_label": "Grab the deal"},
                    "fr": {"title": "Offres du jour", "subtitle": "Ventes flash chronométrées sur le matériel que vous vouliez déjà.", "chip": "Jusqu'à −25 %", "cta_label": "Profiter de l'offre"},
                    "ar": {"title": "عروض اليوم", "subtitle": "تخفيضات مؤقتة على الأجهزة التي أردتها دائمًا.", "chip": "خصم حتى 25%", "cta_label": "اغتنم العرض"},
                },
                "/deals",
                1,
                "1511707171634-5f897ff02aa9",
            ),
            (
                {
                    "en": {"title": "Work sharp, travel light", "subtitle": "Laptops and monitors for people who notice the difference.", "chip": "Computing", "cta_label": "Explore"},
                    "fr": {"title": "Travaillez net, voyagez léger", "subtitle": "Ordinateurs et écrans pour ceux qui voient la différence.", "chip": "Informatique", "cta_label": "Explorer"},
                    "ar": {"title": "اعمل بحدة، وسافر بخفة", "subtitle": "حواسيب وشاشات لمن يلاحظ الفرق.", "chip": "حواسيب", "cta_label": "استكشف"},
                },
                "/catalog?category=computing",
                2,
                "1496181133206-80ce9b88a853",
            ),
        ]
        for translations, cta_to, sort, photo_id in banners:
            banner = await Banner.create(
                translations=translations, cta_to=cta_to, sort=sort, active=True
            )
            url = f"https://images.unsplash.com/photo-{photo_id}?w=1600&h=700&fit=crop&q=80"
            for _attempt in range(3):
                if await images.download_and_attach(
                    banner, url, file_name=f"banner-{sort}.jpg", collection=HERO
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
        ar: str | None = None,
    ) -> Category:
        translations: dict[str, dict[str, str]] = {"en": {"name": name}}
        if fr:
            translations["fr"] = {"name": fr}
        if ar:
            translations["ar"] = {"name": ar}
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
        fr: str | None = None,
        ar: str | None = None,
    ) -> Product:
        slug = name.lower().replace(" ", "-")
        translations: dict[str, dict[str, str]] = {
            "en": {
                "name": name,
                "description": f"{name} — considered design, built to last.",
            }
        }
        if fr:
            translations["fr"] = {
                "name": fr,
                "description": f"{fr} — un design réfléchi, fait pour durer.",
            }
        if ar:
            translations["ar"] = {
                "name": ar,
                "description": f"{ar} — تصميم مدروس، صُنع ليدوم.",
            }
        return await Product.create(
            translations=translations,
            slug=slug,
            category_id=category_id,
            vendor_id=vendor_id,
            price_cents=price_cents,
            currency="USD",
            status="active" if published else "draft",
            published=published,
        )
