"""Seeds the two shipping methods the storefront offers. `standard` @ 500c equals today's flat
rate (the default checkout path is unchanged); `express` @ 1500c is the faster, pricier option."""

from arvel.database import Seeder

from app.models.shipping_method import ShippingMethod

METHODS = [
    {"code": "standard", "name": "Standard", "rate_cents": 500, "sort": 0},
    {"code": "express", "name": "Express", "rate_cents": 1500, "sort": 1},
]


class ShippingMethodsSeeder(Seeder):
    """Idempotent: safe to re-run (each code is first-or-created)."""

    async def run(self) -> None:
        for method in METHODS:
            if await ShippingMethod.where("code", method["code"]).first() is None:
                await ShippingMethod.create(**method)
