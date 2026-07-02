"""Observability — telemetry spans across the request → checkout → DB lifecycle, captured through
an in-memory span exporter (the same code path that ships spans over OTLP to Grafana Tempo/Jaeger).
Proves the custom `checkout.place_order` business span is emitted with its attributes and that the
auto-instrumented DB queries nest under it.
"""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from tests.checkout_helpers import checkout_body


@pytest.fixture
def spans():
    from opentelemetry import trace
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from arvel.telemetry import configure

    configure(
        exporter=InMemorySpanExporter()
    )  # enable tracing + a real provider (once per process)
    exporter = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'obs.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(db)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts"
        )
        p = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee"}},
            slug="tee",
            price_cents=2000,
            currency="USD",
            status=ProductStatus.ACTIVE,
        )
        await ProductVariant.create(
            product_id=p.id, sku="TEE-S", name="S", price_adjustment_cents=0, stock=100
        )
        for model in (User, Category, Product, ProductVariant):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def test_checkout_emits_a_business_span_with_db_children(client, spans) -> None:
    token = client.post(
        "/api/login", json={"email": "cara@example.com", "password": "secret-cara"}
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 2},
        headers=headers,
    )
    assert client.post("/api/checkout", json=checkout_body(), headers=headers).status_code == 201

    finished = spans.get_finished_spans()
    by_name = {s.name: s for s in finished}
    # the custom business span carries its attributes
    assert "checkout.place_order" in by_name
    checkout_span = by_name["checkout.place_order"]
    assert checkout_span.attributes["checkout.total_cents"] == 4900  # 4000 + 500 ship + 400 tax
    assert checkout_span.attributes["checkout.line_count"] == 1
    # arvel auto-instruments DB queries → CLIENT spans were emitted during checkout
    assert any(s.name.startswith("db ") for s in finished)
