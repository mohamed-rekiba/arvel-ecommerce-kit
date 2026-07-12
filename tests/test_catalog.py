"""Catalog read API — exercised through the real served HTTP path (litestar TestClient over the
app built by the production bootstrap). Seeds a deterministic catalog into a temp sqlite file the
served app reads, then asserts search, filtering, pagination shape, eager-loading, and 404s.
"""

import asyncio
import os

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'catalog.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def migrate_and_seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (Category, Product, ProductVariant):
            model.set_connection(db)
        shirts = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        await Category.create(
            translations={"en": {"name": "Shoes"}}, slug="shoes", published=True
        )  # empty → still hidden
        # 25 active "Aero" products (to test pagination) + 1 draft (to test the status filter)
        for i in range(25):
            p = await Product.create(
                category_id=shirts.id,
                translations={
                    "en": {
                        "name": f"Aero Shirt {i:02d}",
                        "description": "A breathable shirt.",
                    }
                },
                slug=f"aero-shirt-{i:02d}",
                price_cents=1999 + i,
                currency="USD",
                status=ProductStatus.ACTIVE,
                published=True,  # retrievable (published, category published, no vendor = first-party)
            )
            await ProductVariant.create(
                product_id=p.id, sku=f"AERO-{i:02d}-S", name="Small", stock=10
            )
        await Product.create(
            category_id=shirts.id,
            translations={
                "en": {"name": "Secret Draft Shirt", "description": "not public yet"}
            },
            slug="secret-draft",
            price_cents=5000,
            currency="USD",
            status=ProductStatus.DRAFT,
            published=False,  # not retrievable → hidden from the storefront
        )
        for model in (Category, Product, ProductVariant):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(migrate_and_seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def test_categories_index(client) -> None:
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    names = [c["translation"]["name"] for c in resp.json()]
    assert names == ["Shirts"]  # Shoes is empty (no retrievable products) → hidden


def test_products_index_paginates_active_only(client) -> None:
    resp = client.get("/api/products")
    assert resp.status_code == 200
    body = resp.json()
    # the length-aware paginator JSON shape
    assert body["per_page"] == 15
    assert body["current_page"] == 1
    assert body["total"] == 25  # 25 retrievable; the unpublished draft is excluded
    assert len(body["data"]) == 15
    # eager-loaded relations are present on each row
    first = body["data"][0]
    assert first["category"]["slug"] == "shirts"
    assert isinstance(first["variants"], list) and first["variants"][0][
        "sku"
    ].startswith("AERO-")


def test_products_index_second_page(client) -> None:
    body = client.get("/api/products?page=2").json()
    assert body["current_page"] == 2
    assert len(body["data"]) == 10  # 25 active - 15 on page 1


def test_products_search_filters_by_name(client) -> None:
    body = client.get("/api/products?q=Aero Shirt 07").json()
    assert body["total"] == 1
    assert body["data"][0]["slug"] == "aero-shirt-07"


def test_unpublished_product_is_hidden_from_the_storefront(client) -> None:
    # the draft never appears in the list, and its detail page 404s (not public)
    body = client.get("/api/products").json()
    assert "secret-draft" not in {p["slug"] for p in body["data"]}
    assert client.get("/api/products/secret-draft").status_code == 404


def test_product_show_eager_loads_and_404s(client) -> None:
    ok = client.get("/api/products/aero-shirt-03")
    assert ok.status_code == 200
    product = ok.json()
    assert product["slug"] == "aero-shirt-03"
    assert product["status"] == "active"  # enum cast serializes to its string value
    assert product["category"]["translation"]["name"] == "Shirts"
    assert product["variants"][0]["stock"] == 10

    missing = client.get("/api/products/does-not-exist")
    assert missing.status_code == 404


# --- infinite-scroll feed: keyset (cursor) pagination, exercised through the served path ---


async def _insert_product(url: str, *, slug: str, price_cents: int) -> None:
    """Insert one retrievable product into the DB the served app reads (for the drift test)."""
    db = ConnectionResolver({"default": {"url": url}})
    for model in (Category, Product, ProductVariant):
        model.set_connection(db)
    shirts = await Category.where("slug", "shirts").first_or_fail()
    p = await Product.create(
        category_id=shirts.id,
        translations={"en": {"name": slug, "description": "inserted mid-scroll."}},
        slug=slug,
        price_cents=price_cents,
        currency="USD",
        status=ProductStatus.ACTIVE,
        published=True,
    )
    await ProductVariant.create(
        product_id=p.id, sku=f"{slug}-S", name="Small", stock=10
    )
    for model in (Category, Product, ProductVariant):
        model.set_connection(None)
    await db.dispose()


def test_products_feed_walks_every_page_once_via_cursor(client) -> None:
    """Walking next_cursor visits all 25 retrievable products exactly once, in slug order, and the
    feed ends with a null cursor. Default sort 'featured' = slug asc (+ pk tiebreaker)."""
    seen: list[str] = []
    cursor: str | None = None
    pages = 0
    while True:
        params: dict[str, object] = {"per_page": 10}
        if cursor:
            params["cursor"] = cursor
        body = client.get("/api/products/feed", params=params).json()
        pages += 1
        assert body["per_page"] == 10
        seen.extend(p["slug"] for p in body["data"])
        cursor = body.get("next_cursor")
        if not cursor:
            break
        assert pages < 10, "cursor never terminated"
    assert pages == 3  # 10 + 10 + 5
    assert seen == [f"aero-shirt-{i:02d}" for i in range(25)]  # full, ordered, no dupes


def test_products_feed_is_drift_free_when_a_row_is_inserted_mid_scroll(client) -> None:
    """The reason to prefer a cursor over offset: a product inserted *before* the cursor boundary
    between page loads must NOT make page 2 repeat or skip a row. Offset(page=2) would duplicate the
    boundary row; keyset seeks past the last-seen slug, so it stays exact."""
    page1 = client.get("/api/products/feed", params={"per_page": 10}).json()
    page1_slugs = [p["slug"] for p in page1["data"]]
    assert page1_slugs == [f"aero-shirt-{i:02d}" for i in range(10)]
    cursor = page1["next_cursor"]
    assert cursor

    # a new product that sorts within the already-seen window (before the cursor boundary)
    asyncio.run(
        _insert_product(
            os.environ["DATABASE_URL"], slug="aero-shirt-05a", price_cents=2000
        )
    )

    page2 = client.get(
        "/api/products/feed", params={"per_page": 10, "cursor": cursor}
    ).json()
    page2_slugs = [p["slug"] for p in page2["data"]]
    # no overlap with page 1, and the freshly-inserted early row does NOT reappear (it's behind the
    # cursor) — exactly the rows offset paging would have drifted over.
    assert set(page1_slugs).isdisjoint(page2_slugs)
    assert "aero-shirt-05a" not in page2_slugs
    assert page2_slugs == [f"aero-shirt-{i:02d}" for i in range(10, 20)]


def test_translation_carries_the_winning_locale(client) -> None:
    """The storefront projection reports WHICH locale it served: the requested one when present,
    the default when the fallback fired — `""` tells an API consumer nothing. One product carries
    real `fr` content so the requested-locale branch is distinguished from the fallback branch
    (an en-only catalog would let a hardcoded default pass every assertion)."""
    import asyncio as _asyncio

    from arvel.database import ConnectionResolver as _CR

    async def seed_fr() -> None:
        db = _CR({"default": {"url": os.environ["DATABASE_URL"]}})
        Product.set_connection(db)
        Category.set_connection(db)
        shirts = await Category.where(slug="shirts").first()
        await Product.create(
            category_id=shirts.id,
            translations={"en": {"name": "Bilingue"}, "fr": {"name": "Bilingue FR"}},
            slug="bilingue",
            price_cents=1000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )

    _asyncio.run(seed_fr())

    products = client.get("/api/products?per_page=50", headers={"accept-language": "en"}).json()[
        "data"
    ]
    assert products and all(p["translation"]["locale"] == "en" for p in products)

    # the requested-locale branch: the bilingual product serves fr and SAYS fr;
    # en-only products serve the en fallback and say so
    fr = client.get("/api/products?per_page=50", headers={"accept-language": "fr"}).json()["data"]
    by_slug = {p["slug"]: p["translation"] for p in fr}
    assert by_slug["bilingue"]["locale"] == "fr"
    assert by_slug["bilingue"]["name"] == "Bilingue FR"
    en_only = [t for slug, t in by_slug.items() if slug != "bilingue"]
    assert en_only and all(t["locale"] == "en" for t in en_only)

    categories = client.get("/api/categories", headers={"accept-language": "en"}).json()
    assert categories and all(c["translation"]["locale"] == "en" for c in categories)
