"""K14 — feature flags for a storefront experiment, live: the "promoted-deals" flag gates the
public Deals-of-the-Day rail's ORDER (percent_off desc for the enabled segment, ends_at otherwise)
per shopper, and a runtime toggle flips one shopper without a redeploy. Needs a REAL Postgres —
the `database` store driver is what makes a toggle issued out-of-band visible to the next served
request; the in-memory `array` driver can't cross that boundary."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from arvel.database import ConnectionResolver, Migrator, discover_migrations
from arvel.dates import Date

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.deal import Deal
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User

pytestmark = pytest.mark.integration

_MODELS = (User, Category, Product, ProductVariant, Deal)


async def _seed(url: str) -> dict[str, int]:
    """Migrate + seed 2 live deals whose ends_at and percent_off DISAGREE on order, an
    enabled-segment shopper (locale=en) and a control shopper (locale=ar)."""
    db = ConnectionResolver({"default": {"url": url}})
    migrator = Migrator(db)
    await (
        migrator.drop_all()
    )  # the PG container is session-scoped; each test starts clean
    await migrator.run(discover_migrations(["database/migrations"]))
    for model in _MODELS:
        model.set_connection(db)
    try:
        amina = await User.create(
            name="Amina",
            email="amina@example.com",
            password="secret-amina",
            role=UserRole.CUSTOMER,
            locale="en",
        )
        bilal = await User.create(
            name="Bilal",
            email="bilal@example.com",
            password="secret-bilal",
            role=UserRole.CUSTOMER,
            locale="ar",
        )
        cat = await Category.create(
            translations={"en": {"name": "Gear"}}, slug="gear", published=True
        )
        now = Date.now()
        # soonest-ending, smallest discount
        soon = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Soon"}},
            slug="soon",
            price_cents=1000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        await ProductVariant.create(
            product_id=soon.id,
            sku="SOON-1",
            name="One",
            price_adjustment_cents=0,
            stock=10,
        )
        soon_deal = await Deal.create(
            product_id=soon.id,
            percent_off=10,
            starts_at=now.subtract(hours=1),
            ends_at=now.add(hours=1),
            active=True,
        )
        # latest-ending, biggest discount — ends_at and percent_off disagree on order
        best = await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Best"}},
            slug="best",
            price_cents=1000,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        await ProductVariant.create(
            product_id=best.id,
            sku="BEST-1",
            name="One",
            price_adjustment_cents=0,
            stock=10,
        )
        best_deal = await Deal.create(
            product_id=best.id,
            percent_off=50,
            starts_at=now.subtract(hours=1),
            ends_at=now.add(hours=2),
            active=True,
        )
        # on PG the retrievable_* views are MATERIALIZED — recompute so storefront reads see the seed
        import sqlalchemy as sa
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.execute(
                sa.text("REFRESH MATERIALIZED VIEW retrievable_products")
            )
            await conn.execute(
                sa.text("REFRESH MATERIALIZED VIEW retrievable_categories")
            )
        await engine.dispose()
        return {
            "soon_deal_id": soon_deal.id,
            "best_deal_id": best_deal.id,
            "amina_id": amina.id,
            "bilal_id": bilal.id,
        }
    finally:
        for model in _MODELS:
            model.set_connection(None)
        await db.dispose()


async def _feature_scopes(url: str) -> set[str]:
    """The scope keys with a persisted `promoted-deals` row — proves the DB driver actually
    stored a value, not an in-process array."""
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url)
    async with engine.begin() as conn:
        rows = (
            await conn.execute(
                sa.text("SELECT scope FROM features WHERE name = 'promoted-deals'")
            )
        ).fetchall()
    await engine.dispose()
    return {row[0] for row in rows}


def _login(
    client: Any, email: str, password: str, *, accept_language: str
) -> dict[str, str]:
    # /api/login syncs the user's locale to the request's active locale on sign-in ("the
    # sign-in language becomes the mail/notification language" — routes/api.py::login) — send
    # the seeded locale back so it doesn't clobber what _seed() set.
    token = client.post(
        "/api/login",
        json={"email": email, "password": password},
        headers={"Accept-Language": accept_language},
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_promoted_deals_flag_gates_order_and_flips_at_runtime(
    postgres_url: str, kit_app: Any
) -> None:
    seeded = asyncio.run(_seed(postgres_url))
    control_order = [
        seeded["soon_deal_id"],
        seeded["best_deal_id"],
    ]  # ends_at ascending
    variant_order = [
        seeded["best_deal_id"],
        seeded["soon_deal_id"],
    ]  # percent_off descending

    with kit_app(DATABASE_URL=postgres_url) as client:
        amina = _login(
            client, "amina@example.com", "secret-amina", accept_language="en"
        )
        bilal = _login(
            client, "bilal@example.com", "secret-bilal", accept_language="ar"
        )

        amina_order = [d["id"] for d in client.get("/api/deals", headers=amina).json()]
        bilal_order = [d["id"] for d in client.get("/api/deals", headers=bilal).json()]
        assert amina_order == variant_order  # enabled segment (locale=en) → variant
        assert bilal_order == control_order  # control segment (locale=ar) → control
        assert amina_order != bilal_order  # non-vacuous: the two orders actually differ

        # runtime toggle, out-of-band: flip AMINA'S OWN scope (not activate_for_everyone — the
        # resolver already persisted her value on the read above, which an everyone row can't
        # override), in a SEPARATE task from the next read (the manager memoizes per-request).
        async def _deactivate_for_amina() -> None:
            from arvel.features import Feature

            user = await User.where("email", "amina@example.com").first()
            await Feature.deactivate("promoted-deals", scope=user)

        with client.portal() as portal:
            portal.call(_deactivate_for_amina)

        amina_after_toggle = [
            d["id"] for d in client.get("/api/deals", headers=amina).json()
        ]
        assert amina_after_toggle == control_order  # flipped without a redeploy

    scopes = asyncio.run(_feature_scopes(postgres_url))
    assert scopes == {f"User:{seeded['amina_id']}", f"User:{seeded['bilal_id']}"}
