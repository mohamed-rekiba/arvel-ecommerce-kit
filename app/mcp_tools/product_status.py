"""A product-status tool this app exposes to AI agents.

Every module under ``app/mcp_tools/`` is autoloaded at boot, so this file is live
the moment it exists — no config wiring needed.

Least-privilege by design: narrow read-only lookups, never generic escapes.
Tool arguments arrive schema-validated, but treat them like route input —
authorize and bound everything here.
"""

from __future__ import annotations

from arvel_ai.mcp import mcp_tool

from app.models.product import Product


@mcp_tool(description="Public availability summary for a product, by slug")
async def product_status(slug: str) -> str:
    product = await Product.where("slug", slug).first()
    if product is None or not product.published:
        return "product not found"
    # .value, not the raw enum member — this is a public summary
    return f"{product.slug}: status={product.status.value}, price_cents={product.price_cents}"
