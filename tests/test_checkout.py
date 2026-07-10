"""Checkout & orders through the real served path. Exercises DB transactions (cart→order is
atomic), events (order.placed → the listener bumps a cache counter), and the OrderStatus state
machine (valid transitions allowed, illegal ones 422), with admin-guarded status changes.
"""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.shipping_method import ShippingMethod
from app.models.user import User
from tests.rbac_helpers import seed_rbac
from tests.checkout_helpers import checkout_body


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'checkout.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def migrate_and_seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        for model in (User, Category, Product, ProductVariant, ShippingMethod):
            model.set_connection(db)
        await seed_rbac(db)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,
        )
        admin = await User.create(
            name="Admin",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("super-admin")  # orders.update authority (bypasses)
        cat = await Category.create(
            translations={"en": {"name": "Shirts"}}, slug="shirts", published=True
        )
        p = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Tee"}},
            slug="tee",
            price_cents=2000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,  # retrievable → the PDP read-back in the cancel test works
        )
        await ProductVariant.create(
            product_id=p.id, sku="TEE-S", name="S", price_adjustment_cents=0, stock=100
        )
        await ShippingMethod.create(
            code="standard", name="Standard", rate_cents=500, active=True, sort=0
        )
        for model in (User, Category, Product, ProductVariant, ShippingMethod):
            model.set_connection(None)
        await db.dispose()

    asyncio.run(migrate_and_seed())

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _login(client, email, password) -> dict:
    token = client.post(
        "/api/login", json={"email": email, "password": password}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_checkout_creates_order_clears_cart_and_fires_event(client) -> None:
    headers = _login(client, "cara@example.com", "secret-cara")
    assert client.get("/api/metrics/orders-placed").json()["orders_placed"] == 0

    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 3},
        headers=headers,
    )

    placed = client.post("/api/checkout", json=checkout_body(), headers=headers)
    assert placed.status_code == 201
    order = placed.json()
    assert order["status"] == "pending"
    # S3: the money breakdown is server-computed — subtotal + flat shipping + 10% tax = total
    assert order["subtotal_cents"] == 6000
    assert order["shipping_cents"] == 500
    assert order["tax_cents"] == 600
    assert order["total_cents"] == 7100
    assert order["currency"] == "USD"
    # the account email was defaulted as the contact and the address persisted
    assert order["contact_email"] == "cara@example.com"
    assert order["address"]["city"] == "Portland"
    assert order["items"][0]["quantity"] == 3

    # the cart was cleared atomically with the order's creation
    assert client.get("/api/cart", headers=headers).json()["items"] == []
    # the order.placed event fired and its listener bumped the metric (event → listener proven)
    assert client.get("/api/metrics/orders-placed").json()["orders_placed"] == 1
    # the order shows up in the user's order list
    orders = client.get("/api/orders", headers=headers).json()
    assert len(orders) == 1 and orders[0]["id"] == order["id"]


def test_checkout_validates_address_and_country(client) -> None:
    """S3 failure paths: missing address fields and unsupported countries are field-level 422s —
    and nothing is created or decremented."""
    headers = _login(client, "cara@example.com", "secret-cara")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=headers,
    )
    # missing city + postal code
    body = checkout_body()
    body["address"]["city"] = ""
    body["address"]["postal_code"] = ""
    resp = client.post("/api/checkout", json=body, headers=headers)
    assert resp.status_code == 422
    assert {"city", "postal_code"} <= set(resp.json()["errors"])

    # a country outside the closed CountryCode set
    resp = client.post(
        "/api/checkout",
        json=checkout_body(address={**checkout_body()["address"], "country": "XX"}),
        headers=headers,
    )
    assert resp.status_code == 422
    assert "country" in resp.json()["errors"]

    # nothing happened: the cart is intact and no order exists
    assert len(client.get("/api/cart", headers=headers).json()["items"]) == 1
    assert client.get("/api/orders", headers=headers).json() == []


def test_checkout_empty_cart_is_422(client) -> None:
    headers = _login(client, "cara@example.com", "secret-cara")
    assert (
        client.post("/api/checkout", json=checkout_body(), headers=headers).status_code
        == 422
    )


def test_order_state_machine(client) -> None:
    customer = _login(client, "cara@example.com", "secret-cara")
    admin = _login(client, "admin@example.com", "secret-admin")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=customer,
    )
    order_id = client.post(
        "/api/checkout", json=checkout_body(), headers=customer
    ).json()["id"]

    # a customer cannot change status (admin-only)
    assert (
        client.post(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "paid"},
            headers=customer,
        ).status_code
        == 403
    )

    # illegal transition pending -> delivered is rejected
    assert (
        client.post(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "delivered"},
            headers=admin,
        ).status_code
        == 422
    )

    # legal path: pending -> paid -> shipped -> delivered
    for nxt in ("paid", "shipped", "delivered"):
        body = {"status": nxt}
        if nxt == "shipped":
            body["tracking_number"] = "1Z999AA10123456784"
        resp = client.post(
            f"/api/admin/orders/{order_id}/status", json=body, headers=admin
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == nxt

    # delivered is terminal — no further transition
    assert (
        client.post(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "cancelled"},
            headers=admin,
        ).status_code
        == 422
    )

    # an unknown status is 422
    assert (
        client.post(
            f"/api/admin/orders/{order_id}/status",
            json={"status": "bogus"},
            headers=admin,
        ).status_code
        == 422
    )


def test_admin_lists_all_orders(client) -> None:
    # a customer places an order
    customer = _login(client, "cara@example.com", "secret-cara")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 2},
        headers=customer,
    )
    order_id = client.post(
        "/api/checkout", json=checkout_body(), headers=customer
    ).json()["id"]

    # the admin (orders.view via super-admin) sees it in the back-office list
    admin = _login(client, "admin@example.com", "secret-admin")
    orders = client.get("/api/admin/orders", headers=admin)
    assert orders.status_code == 200
    ids = {o["id"] for o in orders.json()}
    assert order_id in ids

    # a customer cannot list all orders (lacks orders.view)
    assert client.get("/api/admin/orders", headers=customer).status_code == 403


def test_shipping_an_order_notifies_the_customer(client) -> None:
    """The database channel of the notification system: shipping an order stores a notification the
    customer sees in /api/notifications, and mark-read clears the unread state."""
    customer = _login(client, "cara@example.com", "secret-cara")
    admin = _login(client, "admin@example.com", "secret-admin")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=customer,
    )
    order_id = client.post(
        "/api/checkout", json=checkout_body(), headers=customer
    ).json()["id"]

    # no notifications yet
    assert client.get("/api/notifications", headers=customer).json() == []

    # advance pending → paid → shipped (the shipped transition notifies)
    for nxt in ("paid", "shipped"):
        body = {"status": nxt}
        if nxt == "shipped":
            body["tracking_number"] = "1Z999AA10123456784"
        assert (
            client.post(
                f"/api/admin/orders/{order_id}/status",
                json=body,
                headers=admin,
            ).status_code
            == 200
        )

    notes = client.get("/api/notifications", headers=customer).json()
    assert len(notes) == 1
    note = notes[0]
    assert note["type"] == "OrderShippedNotification"
    assert f"#{order_id}" in note["message"]
    assert note["read"] is False

    # mark all read
    assert client.post("/api/notifications/read", headers=customer).status_code == 200
    assert client.get("/api/notifications", headers=customer).json()[0]["read"] is True

    # a different customer sees none of it (scoped by notifiable)
    other = _login(client, "admin@example.com", "secret-admin")
    assert client.get("/api/notifications", headers=other).json() == []


def test_customer_cancels_a_pending_order_and_stock_returns(client) -> None:
    """S5: the owner cancels while the state machine allows it; the decremented stock returns."""
    customer = _login(client, "cara@example.com", "secret-cara")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 3},
        headers=customer,
    )
    order = client.post("/api/checkout", json=checkout_body(), headers=customer).json()

    cancelled = client.post(f"/api/orders/{order['id']}/cancel", headers=customer)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    # stock restored: the PDP variant shows the pre-checkout quantity again
    product = client.get("/api/products/tee").json()
    assert product["variants"][0]["stock"] == 100

    # a cancelled order is terminal — cancelling again is a state-machine 422
    again = client.post(f"/api/orders/{order['id']}/cancel", headers=customer)
    assert again.status_code == 422


def test_cancel_denies_non_owners_and_shipped_orders(client) -> None:
    """S5 failure paths: deny model for strangers; shipped orders can't be cancelled."""
    customer = _login(client, "cara@example.com", "secret-cara")
    admin = _login(client, "admin@example.com", "secret-admin")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=customer,
    )
    order_id = client.post(
        "/api/checkout", json=checkout_body(), headers=customer
    ).json()["id"]

    # no credentials → 401; a wrong order token → 404
    assert client.post(f"/api/orders/{order_id}/cancel").status_code == 401
    assert (
        client.post(
            f"/api/orders/{order_id}/cancel", headers={"X-Order-Token": "wrong"}
        ).status_code
        == 404
    )

    # ship it (admin) — now the customer can no longer cancel
    for nxt in ("paid", "shipped"):
        body = {"status": nxt}
        if nxt == "shipped":
            body["tracking_number"] = "1Z999AA10123456784"
        client.post(f"/api/admin/orders/{order_id}/status", json=body, headers=admin)
    resp = client.post(f"/api/orders/{order_id}/cancel", headers=customer)
    assert resp.status_code == 422
    assert "no longer" in resp.json()["errors"]["order"][0]


def test_order_lines_carry_the_purchase_snapshot(client) -> None:
    """S5: order lines snapshot the product + variant names at purchase time."""
    customer = _login(client, "cara@example.com", "secret-cara")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=customer,
    )
    order = client.post("/api/checkout", json=checkout_body(), headers=customer).json()
    line = order["items"][0]
    assert (line["product_name"], line["variant_name"]) == ("Tee", "S")


def test_admin_order_detail_shows_everything(client) -> None:
    """S14: lines with purchase snapshots, breakdown, contact/address, customer link, payment
    records, and the transition history — behind orders.view (deny model proven)."""
    customer = _login(client, "cara@example.com", "secret-cara")
    admin = _login(client, "admin@example.com", "secret-admin")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 2},
        headers=customer,
    )
    order_id = client.post(
        "/api/checkout", json=checkout_body(), headers=customer
    ).json()["id"]
    client.post(
        f"/api/admin/orders/{order_id}/status", json={"status": "paid"}, headers=admin
    )

    detail = client.get(f"/api/admin/orders/{order_id}", headers=admin)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["customer"]["email"] == "cara@example.com"
    assert body["items"][0]["product_name"] == "Tee"
    assert body["address"]["city"] == "Portland"
    assert body["payments"] == []  # never paid through the gateway in this test
    # the discount breakdown is part of the admin detail (0/None without a coupon)
    assert (body["coupon_code"], body["discount_cents"]) == (None, 0)
    # the transition is in the history with its properties
    changes = [e for e in body["history"] if e["description"] == "order status changed"]
    assert changes and changes[-1]["properties"] == {"from": "pending", "to": "paid"}
    # timestamps are standard ISO-8601, not the arvel Date repr / RFC-9557 form
    when = changes[-1]["created_at"]
    assert when and "Date(" not in when and "[" not in when

    # a guest order labels the contact and has no customer link
    guest_cart = client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}
    ).json()["cart_token"]
    guest_order = client.post(
        "/api/checkout",
        json=checkout_body(email="guest@example.com"),
        headers={"X-Cart-Token": guest_cart},
    ).json()
    guest_detail = client.get(
        f"/api/admin/orders/{guest_order['id']}", headers=admin
    ).json()
    assert guest_detail["customer"] is None
    assert guest_detail["contact_email"] == "guest@example.com"

    # deny model: a customer (no orders.view) 403s; a guest 401s
    assert (
        client.get(f"/api/admin/orders/{order_id}", headers=customer).status_code == 403
    )
    assert client.get(f"/api/admin/orders/{order_id}").status_code == 401


def test_admin_orders_filter_and_search(client) -> None:
    """v6.1 C — the back-office order list narrows by ?status= and searches ?q= by
    order id or contact email."""
    customer = _login(client, "cara@example.com", "secret-cara")
    ids = []
    for _ in range(2):
        client.post(
            "/api/cart/items",
            json={"product_variant_id": 1, "quantity": 1},
            headers=customer,
        )
        ids.append(
            client.post("/api/checkout", json=checkout_body(), headers=customer).json()[
                "id"
            ]
        )

    admin = _login(client, "admin@example.com", "secret-admin")
    # move one order along so the statuses differ (mark paid via the admin transition)
    client.post(
        f"/api/admin/orders/{ids[0]}/status", json={"status": "paid"}, headers=admin
    )

    paid = client.get("/api/admin/orders?status=paid", headers=admin).json()
    assert {o["id"] for o in paid} == {ids[0]}
    pending = client.get("/api/admin/orders?status=pending", headers=admin).json()
    assert ids[1] in {o["id"] for o in pending} and ids[0] not in {
        o["id"] for o in pending
    }

    # q matches an order id...
    by_id = client.get(f"/api/admin/orders?q={ids[1]}", headers=admin).json()
    assert {o["id"] for o in by_id} == {ids[1]}
    # ...or a contact-email fragment (case-insensitive)
    by_email = client.get("/api/admin/orders?q=CARA@", headers=admin).json()
    assert set(ids) <= {o["id"] for o in by_email}

    # an unknown status is a validation error, not a silent empty list
    assert client.get("/api/admin/orders?status=nope", headers=admin).status_code == 422
