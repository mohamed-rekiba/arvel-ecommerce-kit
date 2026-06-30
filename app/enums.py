"""Closed value sets for the domain — typed as Enums (never bare strings).

arvel casts an ``Enum`` subclass natively: a model field whose ``__casts__`` entry is the Enum
class round-trips value→member on read and member→value on write (see arvel Model._cast_get/_set).
"""

from enum import Enum


class ProductStatus(str, Enum):
    """Lifecycle of a catalog product."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class UserRole(str, Enum):
    """A user's role. Customers self-register; admins are seeded / provisioned via the IdP."""

    CUSTOMER = "customer"
    ADMIN = "admin"


class OrderStatus(str, Enum):
    """An order's lifecycle state."""

    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# The order state machine: which transitions are legal from each state.
ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    return target in ORDER_TRANSITIONS.get(current, set())
