"""Domain models package.

Registers the polymorphic **morph map** at import time: the ``*_type`` columns (media owner, review
subject, activity subject, model_has_roles) store these short class aliases instead of a module
path, so a model move never orphans stored owners. Registering here — rather than in a service
provider — means the aliases are active the moment any model is imported, i.e. before *any* code
(seeders, fixtures, the app) writes or reads a morph type, keeping stored and queried values
consistent. Every model that is ever a morph subject (media owner, review subject, or an
``activity()`` subject) must appear here, or its stored ``*_type`` falls back to the qualified
class path and the admin activity feed shows a mix of aliases and module paths.
"""

from __future__ import annotations

from arvel.database import morph_map

from app.models.banner import Banner
from app.models.category import Category
from app.models.coupon import Coupon
from app.models.deal import Deal
from app.models.order import Order
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.review import Review
from app.models.user import User
from app.models.vendor import Vendor

morph_map(
    {
        "Product": Product,
        "Banner": Banner,
        "User": User,
        "Order": Order,
        "ProductVariant": ProductVariant,
        "Coupon": Coupon,
        "Category": Category,
        "Vendor": Vendor,
        "Deal": Deal,
        "Review": Review,
    }
)
