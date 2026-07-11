"""The Vendor model — a product's seller. A product is retrievable only when its vendor is published."""

from app.observers.publish_observer import PublishObserver
from typing import Any, ClassVar

from arvel import Model


class Vendor(Model):
    # Catalog visibility: a publish change flags the views dirty; the scheduled
    # refresh_if_dirty (routes/console.py) debounces + recomputes.
    __observers__: ClassVar[tuple[type, ...]] = (PublishObserver,)
    __table_name__ = "vendors"
    __fields__: ClassVar[dict[str, type]] = {
        "name": str,
        "slug": str,
        "published": bool,
    }
    __fillable__: ClassVar[list[str]] = ["name", "slug", "published"]
    __casts__: ClassVar[dict[str, Any]] = {"published": bool}

    def products(self) -> Any:
        from app.models.product import Product

        return self.has_many(Product)
