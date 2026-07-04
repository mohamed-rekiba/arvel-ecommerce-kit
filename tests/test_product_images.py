"""The seeder downloads a real image gallery per product (arvel Http client) and attaches it via the
media library (with thumb/preview conversions). The HTTP fetch is faked (MockTransport) so the test
is offline; the media-library store + conversions + retrieval are real.
"""

from io import BytesIO

import httpx
from PIL import Image as PILImage

from arvel.client import Client
from arvel.database import ConnectionResolver, Migrator, discover_migrations
from arvel.kernel import app as app_container
from arvel.kernel import set_application
from arvel.kernel.bootstrap import bootstrap_app

from app.models.category import Category
from app.models.product import IMAGES, Product
from app.models.product_variant import ProductVariant
from app.models.user import User


def _png() -> bytes:
    """A real, valid PNG (generated with PIL) returned by the faked image provider."""
    buf = BytesIO()
    PILImage.new("RGB", (40, 50), "teal").save(buf, format="PNG")
    return buf.getvalue()


_PNG = _png()


async def _seed(url: str, *, handler) -> None:
    from bootstrap.app import create_app
    from database.seeders.database_seeder import DatabaseSeeder

    app = create_app()
    set_application(app)
    bootstrap_app(app)
    await app.boot()
    # rebind AFTER boot — the client provider binds "http" during bootstrap, overwriting an earlier fake
    app.instance("http", Client(transport=httpx.MockTransport(handler)))
    db = ConnectionResolver({"default": {"url": url}})
    await Migrator(db).run(discover_migrations(["database/migrations"]))
    for model in (User, Category, Product, ProductVariant):
        model.set_connection(db)
    await DatabaseSeeder().run()


async def test_seeder_builds_a_real_media_gallery(tmp_path, monkeypatch) -> None:
    url = f"sqlite+aiosqlite:///{tmp_path / 'images.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("FILESYSTEM_LOCAL_ROOT", str(tmp_path / "disk"))

    def ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_PNG, headers={"content-type": "image/png"})

    try:
        await _seed(url, handler=ok)
        product = (await Product.all())[0]
        gallery = await product.get_media(IMAGES)
        assert len(gallery) == 2  # _GALLERY_SIZE images downloaded + attached

        media = gallery[0]
        disk = app_container("filesystem").disk(media.disk)
        # the original + both registered conversions are stored as real, decodable images
        PILImage.open(BytesIO(await disk.get(media.get_path()))).verify()
        for conversion in ("thumb", "preview"):
            path = media.get_path(conversion)
            assert path is not None
            PILImage.open(BytesIO(await disk.get(path))).verify()
    finally:
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(None)
        set_application(None)


async def test_failed_download_does_not_crash_seeding(tmp_path, monkeypatch) -> None:
    """An offline / failing image provider must not crash the seed — products are just image-less."""
    url = f"sqlite+aiosqlite:///{tmp_path / 'imerr.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("FILESYSTEM_LOCAL_ROOT", str(tmp_path / "disk"))

    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    try:
        await _seed(url, handler=down)
        products = await Product.all()
        assert products  # products still seeded
        assert await products[0].get_media(IMAGES) == []  # no images attached, no crash
    finally:
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(None)
        set_application(None)
