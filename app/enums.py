"""Closed value sets for the domain — typed as Enums (never bare strings).

arvel casts an ``Enum`` subclass natively: a model field whose ``__casts__`` entry is the Enum
class round-trips value→member on read and member→value on write (see arvel Model._cast_get/_set).
"""

from enum import Enum


class Currency(str, Enum):
    """Settlement currencies the shop can charge in (the catalog prices in USD today)."""

    USD = "USD"


class CountryCode(str, Enum):
    """Countries the shop ships to (ISO 3166-1 alpha-2) — a closed, validated set."""

    US = "US"
    CA = "CA"
    GB = "GB"
    DE = "DE"
    FR = "FR"
    EG = "EG"


class ProductStatus(str, Enum):
    """Lifecycle of a catalog product."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class UserRole(str, Enum):
    """A user's role. Customers self-register; admins are seeded / provisioned via the IdP."""

    CUSTOMER = "customer"
    ADMIN = "admin"


class Permission(str, Enum):
    """The catalog/back-office permission set (Spatie-style dotted names; roles are grants of these)."""

    CATALOG_VIEW = "catalog.view"
    CATALOG_CREATE = "catalog.create"
    CATALOG_UPDATE = "catalog.update"
    CATALOG_DELETE = "catalog.delete"
    ORDERS_VIEW = "orders.view"
    ORDERS_UPDATE = "orders.update"
    ROLES_MANAGE = "roles.manage"
    AUDIT_VIEW = "audit.view"
    USERS_VIEW = "users.view"
    REVIEWS_MODERATE = "reviews.moderate"


class RoleName(str, Enum):
    """The back-office roles. super-admin is an unconditional bypass (Gate.before)."""

    SUPER_ADMIN = "super-admin"
    CATALOG_MANAGER = "catalog-manager"
    ORDER_MANAGER = "order-manager"
    SUPPORT = "support"


# Which permissions each role grants (super-admin bypasses via Gate.before, so it needs no explicit grants).
ROLE_PERMISSIONS: dict[RoleName, list[Permission]] = {
    RoleName.CATALOG_MANAGER: [
        Permission.CATALOG_VIEW,
        Permission.CATALOG_CREATE,
        Permission.CATALOG_UPDATE,
        Permission.CATALOG_DELETE,
    ],
    RoleName.ORDER_MANAGER: [
        Permission.ORDERS_VIEW,
        Permission.ORDERS_UPDATE,
        Permission.USERS_VIEW,  # an order manager can look up the customer behind an order
    ],
    RoleName.SUPPORT: [
        Permission.CATALOG_VIEW,
        Permission.ORDERS_VIEW,
        Permission.AUDIT_VIEW,
        Permission.USERS_VIEW,  # customer support's whole job
        Permission.REVIEWS_MODERATE,  # user-generated content is a support surface
    ],
}


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


class ReviewStatus(str, Enum):
    """Moderation state of a product review."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CouponType(str, Enum):
    """How a coupon discounts the order."""

    PERCENT = "percent"  # value = percent points (1–100) off the subtotal
    FIXED = "fixed"  # value = cents off (never below zero)


class PaymentStatus(str, Enum):
    """A payment's state, mirrored from the gateway."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
