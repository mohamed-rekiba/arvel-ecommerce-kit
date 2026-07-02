"""The Deal model — a timed percent-off on one product (flash sale)."""

from datetime import datetime
from typing import Any, ClassVar

from arvel import Model


class Deal(Model):
    __table_name__ = "deals"
    __fields__: ClassVar[dict[str, type]] = {
        "product_id": int,
        "percent_off": int,
        "starts_at": datetime,
        "ends_at": datetime,
        "active": bool,
    }
    __fillable__: ClassVar[list[str]] = [
        "product_id",
        "percent_off",
        "starts_at",
        "ends_at",
        "active",
    ]
    __casts__: ClassVar[dict[str, Any]] = {
        "active": bool,
        "starts_at": "datetime",
        "ends_at": "datetime",
    }

    def product(self) -> Any:
        from app.models.product import Product

        return self.belongs_to(Product)
