"""Admin: AI-drafted product copy through the arvel-ai gateway.

The draft is a suggestion returned to the admin UI — nothing is persisted here;
the admin reviews and saves through the normal product update flow.
"""

from __future__ import annotations

from arvel import Schema
from arvel.http import Request

from arvel_ai import AI

from app.models.product import Product
from app.schemas import Translate


class CopyDraft(Schema):
    title: str
    bullets: list[str]


async def copy_draft(request: Request) -> CopyDraft:
    slug = request.path_param("slug")
    product = await Product.where("slug", slug).first_or_fail()
    # translations casts to list[Translate] on the admin path
    translations: list[Translate] = product.translations or []
    name = next(
        (t.name for t in translations if t.locale == "en" and t.name),
        product.slug,
    )
    draft: CopyDraft = await AI.structured(
        CopyDraft,
        f"Write storefront copy for the product {name!r} "
        f"(price: {product.price_cents / 100:.2f} {product.currency}). "
        "A punchy title plus 3 short selling-point bullets.",
        model="fast",
    )
    return draft
