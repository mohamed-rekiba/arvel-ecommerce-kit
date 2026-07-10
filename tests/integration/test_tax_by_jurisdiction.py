"""K17 — tax resolved from the shipping-address jurisdiction, on real Postgres (S1). Same cart,
three shipping countries: US and GB each carry a seeded rate (7% / 20%) so their charged tax
DIFFERS; EG carries no `tax_rates` row so checkout still succeeds at the documented 10% default
(never a 500). A client-injected tax field is proven to have no effect — the server-resolved rate
always wins. Every assertion reads the PERSISTED order row (not just the response DTO)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from tests.checkout_helpers import checkout_body
from tests.integration.test_queue_rail import _seed_shop

pytestmark = pytest.mark.integration

_ADDRESS = {
    "name": "Cara Lund",
    "line1": "12 Linen Way",
    "line2": None,
    "city": "Portland",
    "postal_code": "97201",
}


async def _seed_tax_rates(url: str) -> None:
    """Seed the real `TaxRatesSeeder` — dogfoods the same seeder `db:seed` runs, so the test
    proves the shipped seed data, not a hand-rolled stand-in for it."""
    from arvel.database import ConnectionResolver

    from app.models.tax_rate import TaxRate
    from database.seeders.tax_rates_seeder import TaxRatesSeeder

    db = ConnectionResolver({"default": {"url": url}})
    TaxRate.set_connection(db)
    try:
        await TaxRatesSeeder().run()
    finally:
        TaxRate.set_connection(None)
        await db.dispose()


async def _order_row(url: str, order_id: int) -> dict[str, Any]:
    """Read the order straight off Postgres — the acceptance is on the persisted row, not the
    response DTO (tax_rate_bps isn't even surfaced in OrderOut)."""
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                sa.text(
                    "SELECT subtotal_cents, tax_cents, tax_rate_bps, ship_country "
                    "FROM orders WHERE id = :id"
                ),
                {"id": order_id},
            )
            row = result.mappings().one()
            return dict(row)
    finally:
        await engine.dispose()


def _checkout(client: Any, country: str, **overrides: Any) -> dict[str, Any]:
    address = {**_ADDRESS, "country": country}
    token = client.post(
        "/api/cart/items", json={"product_variant_id": 1, "quantity": 1}
    ).json()["cart_token"]
    body = checkout_body(email=f"{country.lower()}@example.com", address=address)
    body.update(overrides)
    placed = client.post("/api/checkout", json=body, headers={"X-Cart-Token": token})
    assert placed.status_code == 201, placed.text
    return placed.json()


def test_tax_resolves_by_shipping_country_and_defaults_when_unlisted(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_shop(postgres_url))
    asyncio.run(_seed_tax_rates(postgres_url))
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    from litestar.testing import TestClient

    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as client:
        # A — US: seeded 700 bps (7%)
        us_order = _checkout(client, "US")
        us_row = asyncio.run(_order_row(postgres_url, us_order["id"]))
        assert us_row["ship_country"] == "US"
        assert us_row["tax_rate_bps"] == 700
        assert us_row["tax_cents"] == round(us_row["subtotal_cents"] * 700 / 10000)

        # B — GB: seeded 2000 bps (20%) — different rate, different tax, from the SAME cart
        gb_order = _checkout(client, "GB")
        gb_row = asyncio.run(_order_row(postgres_url, gb_order["id"]))
        assert gb_row["tax_rate_bps"] == 2000
        assert gb_row["tax_cents"] == round(gb_row["subtotal_cents"] * 2000 / 10000)
        assert gb_row["tax_cents"] != us_row["tax_cents"]  # A ≠ B, server-computed

        # C — EG: no tax_rates row → the documented 10% default, NOT a 500
        eg_order = _checkout(client, "EG")
        eg_row = asyncio.run(_order_row(postgres_url, eg_order["id"]))
        assert eg_row["tax_rate_bps"] == 1000
        assert eg_row["tax_cents"] == round(eg_row["subtotal_cents"] * 0.10)

        # E — stored == charged for every case above (round-trip on the persisted row)
        for row in (us_row, gb_row, eg_row):
            assert row["tax_cents"] == round(
                row["subtotal_cents"] * row["tax_rate_bps"] / 10000
            )

        # D — a crafted payload carrying tax/rate fields is ignored: US rate wins regardless
        injected_order = _checkout(
            client,
            "US",
            tax_cents=1,
            tax_rate_bps=99999,
            rate=99999,
        )
        injected_row = asyncio.run(_order_row(postgres_url, injected_order["id"]))
        assert (
            injected_row["tax_rate_bps"] == 700
        )  # the jurisdiction rate, not the injected one
        assert injected_row["tax_cents"] == us_row["tax_cents"]
