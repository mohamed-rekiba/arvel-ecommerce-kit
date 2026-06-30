"""Retrievability materialized views (Module C).

A product is **retrievable** only when it is published AND its vendor is published AND its category is
*effective-published* — i.e. the category and **every ancestor** up the tree are published (a recursive
CTE). A category is **retrievable** when it is effective-published AND has at least one retrievable
product somewhere in its subtree (so empty branches hide).

These are Postgres materialized views (refreshed by CatalogVisibilityService); on sqlite the framework
degrades them to plain views, so the same logic runs in the test suite. The storefront reads the views;
the admin reads the base tables (sees everything).
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa

from arvel.database import Migration, Schema

# the views only need the columns that drive retrievability + the keys; they're membership sets, so a
# unique index on id makes them index lookups (EXISTS / refresh CONCURRENTLY).
_categories = sa.table(
    "categories", sa.column("id"), sa.column("parent_id"), sa.column("published")
)
_vendors = sa.table("vendors", sa.column("id"), sa.column("published"))
_products = sa.table(
    "products",
    sa.column("id"),
    sa.column("category_id"),
    sa.column("vendor_id"),
    sa.column("published"),
)


def _truth(col: Any) -> Any:
    """1 when the boolean column is true else 0 — portable AND-via-product across PG/sqlite."""
    return sa.case((col, 1), else_=0)


def _effective_published() -> Any:
    """A CTE of (category_id, eff) where eff=1 iff the category and all its ancestors are published."""
    base = sa.select(
        _categories.c.id.label("origin"),
        _categories.c.parent_id.label("parent_id"),
        _truth(_categories.c.published).label("ok"),
    ).cte("eff_chain", recursive=True)
    parent = _categories.alias("ancestor")
    step = sa.select(
        base.c.origin,
        parent.c.parent_id,
        base.c.ok * _truth(parent.c.published),
    ).select_from(base.join(parent, parent.c.id == base.c.parent_id))
    chain = base.union_all(step)
    return (
        sa.select(
            chain.c.origin.label("category_id"),
            sa.func.min(chain.c.ok).label("eff"),
        )
        .group_by(chain.c.origin)
        .cte("effective_published")
    )


def _retrievable_products_select() -> Any:
    eff = _effective_published()
    return (
        sa.select(_products.c.id, _products.c.category_id)  # membership set: id (+ category_id for the category view)
        .select_from(
            _products.outerjoin(_vendors, _vendors.c.id == _products.c.vendor_id).join(
                eff, eff.c.category_id == _products.c.category_id
            )
        )
        .where(_products.c.published)
        # a vendor, if set, must be published; a first-party product (no vendor) is allowed
        .where(sa.or_(_products.c.vendor_id.is_(None), _vendors.c.published))
        .where(eff.c.eff == 1)
    )


def _retrievable_categories_select() -> Any:
    eff = _effective_published()
    # subtree: (ancestor, descendant) pairs walking DOWN the tree (incl. self)
    sub_base = sa.select(
        _categories.c.id.label("ancestor"),
        _categories.c.id.label("descendant"),
    ).cte("subtree", recursive=True)
    child = _categories.alias("child")
    sub_step = sa.select(sub_base.c.ancestor, child.c.id).select_from(
        sub_base.join(child, child.c.parent_id == sub_base.c.descendant)
    )
    subtree = sub_base.union_all(sub_step)
    rp = sa.table("retrievable_products", sa.column("category_id"))
    has_retrievable_product = (
        sa.select(sa.literal(1))
        .select_from(subtree.join(rp, rp.c.category_id == subtree.c.descendant))
        .where(subtree.c.ancestor == _categories.c.id)
        .exists()
    )
    return (
        sa.select(_categories.c.id)  # membership set
        .select_from(_categories.join(eff, eff.c.category_id == _categories.c.id))
        .where(eff.c.eff == 1)
        .where(has_retrievable_product)
    )


class CreateRetrievableViews(Migration):
    def up(self, schema: Schema) -> None:
        schema.create_materialized_view("retrievable_products", _retrievable_products_select())
        schema.create_materialized_view("retrievable_categories", _retrievable_categories_select())
        if schema.dialect == "postgresql":
            # a unique index on id makes the EXISTS/visibility lookups index scans AND unlocks
            # REFRESH MATERIALIZED VIEW CONCURRENTLY (no read-lock during the debounced refresh).
            schema.execute(sa.text("CREATE UNIQUE INDEX ON retrievable_products (id)"))
            schema.execute(sa.text("CREATE UNIQUE INDEX ON retrievable_categories (id)"))

    def down(self, schema: Schema) -> None:
        keyword = "MATERIALIZED VIEW" if schema.dialect == "postgresql" else "VIEW"
        schema.execute(sa.text(f"DROP {keyword} IF EXISTS retrievable_categories"))
        schema.execute(sa.text(f"DROP {keyword} IF EXISTS retrievable_products"))
