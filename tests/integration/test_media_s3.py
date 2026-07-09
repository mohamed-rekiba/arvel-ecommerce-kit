"""K7 — the kit's media path proven on REAL object storage (RustFS/S3), through the served
endpoints, not `FilesystemManager` directly. Closes the round's stated "config-only, deferred"
gap: `test_rustfs_s3_disk_roundtrip` only proves one flat key, not the media access pattern
(nested `{collection}/{id}/...` + `conversions/*`, reservation-rollback, public-URL build).

Every served-endpoint test boots the app exactly like `tests/test_media.py` (RBAC + admin +
product seed, `TestClient` over `create_app().as_asgi()`), but with `FILESYSTEM_DISK=s3` and
`AWS_*` wired from the `rustfs_s3` fixture on a fresh per-test bucket. Object existence is
checked directly against the store (a fresh `s3fs.S3FileSystem`, independent of arvel's `Media`
abstraction) — the load-bearing assertion the round never made.
"""

from __future__ import annotations

import asyncio
import base64
import uuid
from collections.abc import AsyncIterator
from io import BytesIO
from typing import Any

import pytest
import s3fs
from litestar.testing import TestClient
from PIL import Image as PILImage

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from tests.rbac_helpers import seed_rbac

pytestmark = pytest.mark.integration

# a real 1x1 transparent PNG (same fixture tests/test_media.py uses)
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _large_png() -> bytes:
    """A real, ~750 KB PNG (random pixels compress poorly, unlike the 1x1 smoke fixture) — big
    streamed to a temp file via `sink()` and asserted byte-for-byte equal on S3."""
    import os

    size = 500
    buf = BytesIO()
    PILImage.frombytes("RGB", (size, size), os.urandom(size * size * 3)).save(
        buf, format="PNG"
    )
    return buf.getvalue()


async def _achunks(data: bytes, size: int = 65_536) -> AsyncIterator[bytes]:
    for i in range(0, len(data), size):
        yield data[i : i + size]


# --- served-app boot, mirroring tests/test_media.py's `client` fixture + the rustfs_s3 env wiring
# test_rustfs_s3_disk_roundtrip uses (tests/integration/test_services_smoke.py) -----------------


@pytest.fixture
def s3_media_app(
    rustfs_s3: dict[str, str], monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> Any:
    """Boot the served app with `FILESYSTEM_DISK=s3` on a fresh per-test bucket (created up front
    via a raw `s3fs.mkdir` — RustFS won't auto-create it), seeded with RBAC + an admin + a
    product. Yields ``(client, admin_headers, product_id, bucket, raw_fs)`` — ``raw_fs`` is an
    independent `s3fs.S3FileSystem` for asserting objects physically landed in the bucket."""
    bucket = f"arvel-{uuid.uuid4().hex[:10]}"
    raw_fs = s3fs.S3FileSystem(
        key=rustfs_s3["key"],
        secret=rustfs_s3["secret"],
        client_kwargs={"endpoint_url": rustfs_s3["endpoint"]},
    )
    raw_fs.mkdir(bucket)

    url = f"sqlite+aiosqlite:///{tmp_path / 'media_s3.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("FILESYSTEM_DISK", "s3")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", rustfs_s3["key"])
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", rustfs_s3["secret"])
    monkeypatch.setenv("AWS_ENDPOINT", rustfs_s3["endpoint"])
    monkeypatch.setenv("AWS_BUCKET", bucket)

    async def seed() -> int:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product):
            model.set_connection(db)
        await seed_rbac(db)
        admin = await User.create(
            name="Admin",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("super-admin")  # catalog.update authority (bypasses)
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        product = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee"}},
            slug="tee",
            price_cents=2000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        product_id = int(product.id)
        for model in (User, Category, Product):
            model.set_connection(None)
        await db.dispose()
        return product_id

    product_id = asyncio.run(seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as client:
        token = client.post(
            "/api/login",
            json={"email": "admin@example.com", "password": "secret-admin"},
        ).json()["token"]
        yield client, {"Authorization": f"Bearer {token}"}, product_id, bucket, raw_fs

    # avoid a later test resolving this test's loop-bound engine ("attached to a different loop")
    from arvel.kernel import set_application

    set_application(None)


def _keys(bucket: str, media_id: int, file_name: str) -> list[str]:
    return [
        f"{bucket}/images/{media_id}/{file_name}",
        f"{bucket}/images/{media_id}/conversions/thumb.webp",
        f"{bucket}/images/{media_id}/conversions/preview.webp",
    ]


def test_upload_writes_original_and_conversions_to_s3(s3_media_app: Any) -> None:
    client, headers, product_id, bucket, raw_fs = s3_media_app

    up = client.post(
        f"/api/admin/products/{product_id}/image",
        files={"image": ("logo.png", _PNG, "image/png")},
        headers=headers,
    )
    assert up.status_code == 201, up.text
    media_id = up.json()[0]["id"]

    for key in _keys(bucket, media_id, "logo.png"):
        assert raw_fs.exists(key), key


def test_served_endpoint_streams_webp_from_s3(s3_media_app: Any) -> None:
    client, headers, product_id, bucket, raw_fs = s3_media_app

    up = client.post(
        f"/api/admin/products/{product_id}/image",
        files={"image": ("logo.png", _PNG, "image/png")},
        headers=headers,
    )
    media_id = up.json()[0]["id"]

    original = client.get(f"/api/media/{media_id}")
    assert original.status_code == 200 and original.content == _PNG

    for conversion in ("thumb", "preview"):
        conv = client.get(f"/api/media/{media_id}/{conversion}")
        assert conv.status_code == 200
        assert conv.headers["content-type"] == "image/webp"
        assert PILImage.open(BytesIO(conv.content)).format == "WEBP"


def test_delete_removes_s3_objects(s3_media_app: Any) -> None:
    client, headers, product_id, bucket, raw_fs = s3_media_app

    up = client.post(
        f"/api/admin/products/{product_id}/image",
        files={"image": ("logo.png", _PNG, "image/png")},
        headers=headers,
    )
    media_id = up.json()[0]["id"]
    keys = _keys(bucket, media_id, "logo.png")
    assert all(raw_fs.exists(key) for key in keys)

    deleted = client.delete(
        f"/api/admin/products/{product_id}/media/{media_id}", headers=headers
    )
    assert deleted.status_code == 200

    assert not any(raw_fs.exists(key) for key in keys)
    assert client.get(f"/api/media/{media_id}").status_code == 404


def test_conversion_put_failure_rolls_back_with_no_orphan(
    s3_media_app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The half-written case: the ORIGINAL put succeeds, the first CONVERSION put fails.
    `to_media_collection`'s reservation-rollback must delete the already-written original and the
    reserved row — no orphan object, no orphan row, and a clean (not 500) error to the client."""
    client, headers, product_id, bucket, raw_fs = s3_media_app

    from arvel.filesystem import Filesystem

    original_put = Filesystem.put
    calls = {"n": 0}

    async def _flaky_put(self: Filesystem, path: str, contents: bytes | str) -> str:
        calls["n"] += 1
        if calls["n"] == 2:  # 1st call = the original; 2nd = the first conversion
            raise RuntimeError("simulated S3 outage on the conversion put")
        return await original_put(self, path, contents)

    monkeypatch.setattr(Filesystem, "put", _flaky_put)

    resp = client.post(
        f"/api/admin/products/{product_id}/image",
        files={"image": ("logo.png", _PNG, "image/png")},
        headers=headers,
    )
    assert resp.status_code == 422, (
        resp.text
    )  # a clean client error, not an unhandled 500

    assert raw_fs.find(bucket) == []  # the rolled-back original left no orphan object

    # no orphan row either — the admin media library (catalog.view, super-admin bypasses) lists
    # every Media row across the portfolio
    assert client.get("/api/admin/media", headers=headers).json() == []


async def test_seeder_streams_large_image_to_s3_without_corruption(
    rustfs_s3: dict[str, str], tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """K7 sink() proof: `ProductImageService.download_and_attach` streams the response body to a
    temp file (`Http.sink()`, constant memory) rather than buffering it — a multi-chunk image
    (bigger than one `aiter_bytes` chunk) round-trips byte-for-byte onto the S3 disk."""
    import httpx
    from anyio import to_thread

    from arvel.client import Client
    from arvel.filesystem import FilesystemManager
    from arvel.kernel import set_application
    from arvel.kernel.bootstrap import bootstrap_app

    from app.models.product import IMAGES
    from app.services.product_image_service import ProductImageService

    bucket = f"arvel-{uuid.uuid4().hex[:10]}"
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'large.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("FILESYSTEM_DISK", "s3")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", rustfs_s3["key"])
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", rustfs_s3["secret"])
    monkeypatch.setenv("AWS_ENDPOINT", rustfs_s3["endpoint"])
    monkeypatch.setenv("AWS_BUCKET", bucket)

    from bootstrap.app import create_app

    app = create_app()
    bootstrap_app(app)
    await app.boot()
    try:
        disk = FilesystemManager(app).disk("s3")
        await to_thread.run_sync(disk.fs.mkdir, bucket)

        db = ConnectionResolver({"default": {"url": db_url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (Category, Product):
            model.set_connection(db)
        try:
            cat = await Category.create(
                translations={"en": {"name": "Lighting"}},
                slug="lighting",
                published=True,
            )
            product = await Product.create(
                category_id=cat.id,
                translations={"en": {"name": "Lamp"}},
                slug="lamp",
                price_cents=1000,
                currency="USD",
                status=ProductStatus.ACTIVE,
                published=True,
            )

            source = _large_png()

            async def _stream(request: httpx.Request) -> httpx.Response:
                return httpx.Response(
                    200, content=_achunks(source), headers={"content-type": "image/png"}
                )

            # rebind AFTER boot — the client provider binds "http" during bootstrap
            app.instance("http", Client(transport=httpx.MockTransport(_stream)))

            ok = await ProductImageService().download_and_attach(
                product, "https://cdn.example.test/lamp.png", file_name="lamp.png"
            )
            assert ok is True

            media = (await product.get_media(IMAGES))[0]
            assert await disk.get(media.get_path()) == source
        finally:
            for model in (Category, Product):
                model.set_connection(None)
            await db.dispose()
    finally:
        set_application(None)
