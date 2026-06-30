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
