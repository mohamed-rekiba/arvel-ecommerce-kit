"""DR-0054 regression (arvel FW-binding-auth-ordering): a converted admin route's route-model
binding must not leak resource existence to an unauthenticated caller. Before the fix, a bound id
that didn't exist 404d ahead of the pipeline while an existing one 401d — a zero-credential
existence oracle across K4's ~30 converted admin routes. Pins the closed leak on
``PUT /api/admin/products/{id}`` against the still-uniform un-converted control,
``GET /api/admin/products/{id}`` (manual lookup inside the handler, always after auth)."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.models.category import Category
from app.models.product import Product


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'binding_auth.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def migrate_and_seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (Category, Product):
            model.set_connection(db)
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts"
        )
        await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Existing"}},
            slug="existing",
            price_cents=1000,
            currency="USD",
            status="active",
        )
        for model in (Category, Product):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(migrate_and_seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


NONEXISTENT_ID = 999999


def test_control_route_is_uniform_401_regardless_of_id(client) -> None:
    """The un-converted control (manual lookup inside the handler, after the pipeline) already
    401s uniformly — the baseline the converted route must now match."""
    assert client.get(f"/api/admin/products/{NONEXISTENT_ID}").status_code == 401
    assert client.get("/api/admin/products/1").status_code == 401


def test_converted_route_nonexistent_id_is_401_not_404(client) -> None:
    """The closed leak: PUT /api/admin/products/{id} binds `id` to a `Product` implicitly. Before
    DR-0054, a guest got 404 here for a nonexistent id — proving the id didn't exist without ever
    authenticating."""
    resp = client.put(
        f"/api/admin/products/{NONEXISTENT_ID}",
        json={"translations": {"en": {"name": "x"}}},
    )
    assert resp.status_code == 401


def test_converted_route_existing_id_is_401_uniform_with_nonexistent(client) -> None:
    """Same route, a real id, still no credentials — must 401 exactly like the nonexistent-id
    case above, closing the oracle."""
    resp = client.put(
        "/api/admin/products/1",
        json={"translations": {"en": {"name": "x"}}},
    )
    assert resp.status_code == 401
