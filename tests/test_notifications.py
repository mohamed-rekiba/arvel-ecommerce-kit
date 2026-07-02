"""Mail — an order-confirmation email is sent (via an order.placed listener) on checkout. Uses
arvel's mail fake so no real SMTP is touched, asserting the Mailable was dispatched.
"""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations
from arvel.testing import fake, reset_fakes

from app.enums import ProductStatus, UserRole
from app.mail.order_confirmation import OrderConfirmation
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from tests.checkout_helpers import checkout_body


@pytest.fixture
def faked_mail():
    from arvel.support.facades import Mail

    mailer = fake(Mail)
    yield mailer
    reset_fakes()


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'notify.sqlite'}"
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


def _auth(client) -> dict:
    token = client.post(
        "/api/login", json={"email": "cara@example.com", "password": "secret-cara"}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_checkout_sends_order_confirmation_email(client, faked_mail) -> None:
    headers = _auth(client)
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 2},
        headers=headers,
    )
    assert client.post("/api/checkout", json=checkout_body(), headers=headers).status_code == 201
    # the order.placed listener emailed the confirmation (recorded by the fake, no SMTP)
    faked_mail.assert_sent(OrderConfirmation)
    assert faked_mail.sent[0].order_id is not None


def test_guest_checkout_email_receives_the_confirmation(client, faked_mail) -> None:
    """S3: a guest provides a contact email at checkout — the confirmation goes THERE."""
    token = client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}
    ).json()["cart_token"]
    placed = client.post(
        "/api/checkout",
        json=checkout_body(email="guest@example.com"),
        headers={"X-Cart-Token": token},
    )
    assert placed.status_code == 201
    assert placed.json()["contact_email"] == "guest@example.com"
    faked_mail.assert_sent(OrderConfirmation)
    assert faked_mail.recipients[0] == ["guest@example.com"]


def test_guest_checkout_without_email_is_rejected(client, faked_mail) -> None:
    """S3 failure path: a guest with no contact email gets a field-level 422 — no order, no mail."""
    token = client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}
    ).json()["cart_token"]
    resp = client.post(
        "/api/checkout", json=checkout_body(), headers={"X-Cart-Token": token}
    )
    assert resp.status_code == 422
    assert "email" in resp.json()["errors"]
    faked_mail.assert_nothing_sent()
