"""DR-0055 regression: an authenticated-but-unauthorized caller must get the SAME status for an
existing bound id as for a nonexistent one. K4's route-model binding resolves existence before a
handler runs; a class-level permission check that used to run first (and is now Authorize route
middleware, per DR-0055) must keep denying uniformly — otherwise a logged-in customer can use the
403-vs-404 split as a zero-extra-credential existence oracle (order-id enumeration being the
sharpest case). Covers one Authorize-middleware route per K4 conversion class (an order, a banner)
plus the per-object deny-as-404 case (product update), which was already uniform before this DR
and must stay that way.

K5 folds the per-route Authorize into a per-controller declaration (``api_resource`` +
``Controller.middleware()``/``authorize_resource``) — the parametrized cases below extend the same
oracle-closed assertion to every converted resource's instance actions (update/destroy: the ones
with an id in the path, so the only ones where "existing" vs "nonexistent" is even a question) for
both an authenticated-unauthorized customer and a guest, proving the DR-0056 conversion carried the
DR-0055 contract over rather than reopening it.
"""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations
from arvel.dates import Date

from app.enums import CouponType, ProductStatus, UserRole
from app.models.banner import Banner
from app.models.category import Category
from app.models.coupon import Coupon
from app.models.deal import Deal
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.shipping_method import ShippingMethod
from app.models.user import User
from app.models.vendor import Vendor
from tests.checkout_helpers import checkout_body
from tests.rbac_helpers import seed_rbac

_NONEXISTENT = 999999


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'authz_uniformity.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        models = (
            User,
            Category,
            Product,
            ProductVariant,
            ShippingMethod,
            Banner,
            Vendor,
            Coupon,
            Deal,
        )
        for model in models:
            model.set_connection(db)
        await User.create(
            name="Cara",
            email="cara@example.com",
            password="secret-cara",
            role=UserRole.CUSTOMER,  # authenticated, but no admin permission whatsoever
        )
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
        await ProductVariant.create(
            product_id=product.id,
            sku="TEE-S",
            name="S",
            price_adjustment_cents=0,
            stock=5,
        )
        await Banner.create(
            translations={"en": {"title": "Sale"}},
            cta_to="/catalog",
            sort=0,
            active=True,
        )
        # K5: the class-permission resources newly converted to api_resource — one row each so
        # their update/destroy uniformity cases below have a real id to compare against.
        await Vendor.create(name="Acme", slug="acme", published=True)
        await Coupon.create(
            code="SAVE10",
            type=CouponType.PERCENT,
            value=10,
            usage_limit=None,
            per_customer_limit=None,
            uses=0,
            active=True,
            announce=False,
        )
        now = Date.now()
        await Deal.create(
            product_id=product.id,
            percent_off=20,
            starts_at=now.subtract(hours=1),
            ends_at=now.add(hours=1),
            active=True,
        )
        await ShippingMethod.create(
            code="standard", name="Standard", rate_cents=500, active=True, sort=0
        )
        for model in models:
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client


def _auth(client, email, password):
    token = client.post(
        "/api/login", json={"email": email, "password": password}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_authorize_middleware_route_denies_uniformly(client) -> None:
    """orders.view (Authorize middleware, DR-0055): an unauthorized customer gets the SAME status
    for a real order as for one that doesn't exist — the permission gate, not existence, decides."""
    customer = _auth(client, "cara@example.com", "secret-cara")
    client.post(
        "/api/cart/items",
        json={"product_variant_id": 1, "quantity": 1},
        headers=customer,
    )
    order = client.post("/api/checkout", json=checkout_body(), headers=customer).json()

    existing = client.get(f"/api/admin/orders/{order['id']}", headers=customer)
    missing = client.get(f"/api/admin/orders/{_NONEXISTENT}", headers=customer)
    assert existing.status_code == missing.status_code == 403, (
        existing.status_code,
        missing.status_code,
    )


def test_authorize_middleware_route_denies_uniformly_for_banners(client) -> None:
    """catalog.update on a banner mutation (Authorize middleware, DR-0055) — same uniformity
    guarantee on a second, independent resource family."""
    customer = _auth(client, "cara@example.com", "secret-cara")

    existing = client.patch(
        "/api/admin/banners/1", json={"active": False}, headers=customer
    )
    missing = client.patch(
        f"/api/admin/banners/{_NONEXISTENT}", json={"active": False}, headers=customer
    )
    assert existing.status_code == missing.status_code == 403, (
        existing.status_code,
        missing.status_code,
    )


# K5: the converted class-permission resources' instance actions (update/destroy — the ones with
# an id in the path; index/store take no id, so there's no existing-vs-nonexistent question to ask
# of them). Product and Banner already have dedicated cases above/below; this is the rest of the
# conversion map (category, vendor, coupon, deal).
_K5_INSTANCE_ROUTES = [
    # `update` now registers through api_resource like every other action (DR-0057 fixed the
    # PUT+PATCH operationId collision that used to force these onto an explicit single-verb
    # route). Each case below still calls the resource's original verb — that verb still works,
    # api_resource just also accepts the other one now.
    pytest.param(
        "put", "categories/{id}", {"published": False}, id="categories.update"
    ),
    pytest.param("delete", "categories/{id}", None, id="categories.destroy"),
    pytest.param("put", "vendors/{id}", {"published": False}, id="vendors.update"),
    pytest.param("patch", "coupons/{id}", {"active": False}, id="coupons.update"),
    pytest.param("patch", "deals/{id}", {"active": False}, id="deals.update"),
    pytest.param("delete", "deals/{id}", None, id="deals.destroy"),
]


@pytest.mark.parametrize(("method", "path", "body"), _K5_INSTANCE_ROUTES)
def test_k5_converted_resources_deny_customer_uniformly(
    client, method, path, body
) -> None:
    """Every class-permission resource K5 converted to ``api_resource`` +
    ``Controller.middleware()`` still 403s an authenticated-unauthorized customer uniformly,
    existing id vs nonexistent — the DR-0055 contract, now declared per-controller instead of
    per-route (DR-0056), must still hold."""
    customer = _auth(client, "cara@example.com", "secret-cara")
    call = getattr(client, method)
    kwargs = {"headers": customer, **({"json": body} if body is not None else {})}
    existing = call(f"/api/admin/{path.format(id=1)}", **kwargs)
    missing = call(f"/api/admin/{path.format(id=_NONEXISTENT)}", **kwargs)
    assert existing.status_code == missing.status_code == 403, (
        path,
        existing.status_code,
        missing.status_code,
    )


@pytest.mark.parametrize(("method", "path", "body"), _K5_INSTANCE_ROUTES)
def test_k5_converted_resources_reject_guest_uniformly(
    client, method, path, body
) -> None:
    """Same routes, no credentials: Authenticate still runs as group middleware before route-model
    binding (K4/DR-0054, unaffected by folding Authorize into the controller), so a guest gets a
    uniform 401 regardless of whether the id exists — never a binding-miss 404 leaking existence to
    a caller with zero credentials."""
    call = getattr(client, method)
    kwargs = {"json": body} if body is not None else {}
    existing = call(f"/api/admin/{path.format(id=1)}", **kwargs)
    missing = call(f"/api/admin/{path.format(id=_NONEXISTENT)}", **kwargs)
    assert existing.status_code == missing.status_code == 401, (
        path,
        existing.status_code,
        missing.status_code,
    )


@pytest.mark.parametrize(
    "path",
    [
        "products",
        "categories",
        "vendors",
        "coupons",
        "banners",
        "deals",
    ],
)
def test_k5_converted_resource_index_rejects_guest(client, path) -> None:
    """The class actions (index/store — no id, so no existing/nonexistent dimension) still inherit
    Authenticate from the group after the api_resource conversion; a guest never reaches the
    controller's ``middleware()``/``authorize_resource`` at all."""
    assert client.get(f"/api/admin/{path}").status_code == 401


def test_per_object_policy_route_was_already_uniform(client) -> None:
    """PUT /admin/products/{id}: authorization needs the bound instance (deny_as_not_found), so it
    stays in-handler per DR-0055's exception clause — already uniform (both 404) before this DR,
    confirmed unchanged by it."""
    customer = _auth(client, "cara@example.com", "secret-cara")

    existing = client.put(
        "/api/admin/products/1",
        json={"translations": {"en": {"name": "Hacked"}}},
        headers=customer,
    )
    missing = client.put(
        f"/api/admin/products/{_NONEXISTENT}",
        json={"translations": {"en": {"name": "Hacked"}}},
        headers=customer,
    )
    assert existing.status_code == missing.status_code == 404, (
        existing.status_code,
        missing.status_code,
    )
