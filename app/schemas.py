"""API request + response schemas (arvel.Schema = msgspec.Struct).

These are the typed boundary of the HTTP API: request bodies are parsed + validated into the *In
schemas, and handlers return the *Out schemas — which gives both strict type-safety AND generated
OpenAPI request/response schemas. Models are mapped to these DTOs (never returned raw), so the wire
contract is explicit and decoupled from the storage shape.
"""

from __future__ import annotations

from typing import Any

from arvel import Schema

# --- shared / catalog ---------------------------------------------------------


class Translate(Schema):
    """One locale's translatable fields (the value of `translations[locale]`)."""

    name: str
    description: str | None = None
    locale: str = ""


class CategoryOut(Schema):
    id: int
    slug: str
    translation: Translate


class VariantOut(Schema):
    id: int
    sku: str
    name: str
    price_adjustment_cents: int
    stock: int


class GalleryImageOut(Schema):
    """One product gallery image (media-library) with its conversion URLs."""

    id: int
    url: str
    thumb_url: str
    preview_url: str


class ProductOut(Schema, omit_defaults=True):
    id: int
    slug: str
    translation: Translate  # the active locale's name/description (scope_in_locale)
    price_cents: int
    currency: str
    status: str
    gallery: list[GalleryImageOut]  # always present (possibly empty)
    category: CategoryOut | None = None
    variants: list[VariantOut] | None = None


class ProductPage(Schema):
    """The catalog listing — arvel's LengthAwarePaginator shape, typed."""

    data: list[ProductOut]
    current_page: int
    last_page: int
    per_page: int
    total: int


# --- admin views (all rows, incl. hidden, each annotated with is_visible) ------


class AdminProductOut(Schema):
    """A product as the admin sees it — every row, ALL translations, and `is_visible` (whether the
    storefront shows it: published ∧ vendor published ∧ category chain published)."""

    id: int
    slug: str
    translations: list[Translate]
    status: str
    published: bool
    is_visible: bool


class AdminProductPage(Schema):
    data: list[AdminProductOut]
    current_page: int
    last_page: int
    per_page: int
    total: int


class AdminCategoryOut(Schema):
    id: int
    slug: str
    translations: list[Translate]
    parent_id: int | None = None
    published: bool = False
    is_visible: bool = False


class AdminCategoryPage(Schema):
    data: list[AdminCategoryOut]
    current_page: int
    last_page: int
    per_page: int
    total: int


# --- auth ---------------------------------------------------------------------


class RegisterIn(Schema):
    name: str
    email: str
    password: str


class CredentialsIn(Schema):
    email: str
    password: str


class TokenOut(Schema):
    token: str


class UserOut(Schema):
    id: int
    name: str
    email: str
    phone: str | None
    email_verified: bool


class ProfileIn(Schema):
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class ChangePasswordIn(Schema):
    current_password: str
    password: str


class VerifyEmailIn(Schema):
    token: str


class MessageOut(Schema):
    message: str


class WishlistToggleOut(Schema):
    saved: bool


class NotificationOut(Schema):
    id: str
    type: str
    message: str
    read: bool
    created_at: str | None


# --- RBAC / audit (admin) -----------------------------------------------------


class RoleOut(Schema):
    id: int
    name: str
    permissions: list[str]


class PermissionOut(Schema):
    id: int
    name: str


class AssignRoleIn(Schema):
    role: str


class UserRolesOut(Schema):
    user_id: int
    roles: list[str]


class ActivityOut(Schema):
    id: int
    description: str
    event: str | None
    causer_id: int | None
    subject_type: str | None
    subject_id: int | None
    properties: dict[str, Any]
    created_at: str | None


class ForgotPasswordIn(Schema):
    email: str


class ForgotPasswordOut(Schema):
    message: str  # always the same non-enumerating line; the link itself is emailed


class ResetPasswordIn(Schema):
    token: str
    password: str


# --- cart ---------------------------------------------------------------------


class AddItemIn(Schema):
    product_variant_id: int
    quantity: int = 1


class UpdateItemIn(Schema):
    quantity: int


class CartLineOut(Schema):
    id: int
    product_variant_id: int
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class CartOut(Schema, omit_defaults=True):
    id: int | None
    items: list[CartLineOut]
    total_cents: int
    cart_token: str | None = None


# --- admin products -----------------------------------------------------------


class ProductIn(Schema):
    category_id: int
    name: str
    price_cents: int
    description: str | None = None


class UpdateProductIn(Schema):
    name: str | None = None
    price_cents: int | None = None
    status: str | None = None


# --- checkout / orders / payments ---------------------------------------------


class OrderLineOut(Schema):
    product_variant_id: int
    product_name: str
    variant_name: str
    quantity: int
    unit_price_cents: int


class AddressIn(Schema):
    """Shipping address as submitted — every field optional at the parse layer so the Validator
    can return field-level 422s (not a shapeless 400)."""

    name: str | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None


class CheckoutIn(Schema):
    """Checkout submission: contact email (required for guests; defaults to the account email for
    signed-in customers) + shipping address."""

    email: str | None = None
    address: AddressIn | None = None


class AddressOut(Schema):
    name: str
    line1: str
    line2: str | None
    city: str
    postal_code: str
    country: str


class OrderOut(Schema):
    id: int
    status: str
    token: str
    contact_email: str
    address: AddressOut
    subtotal_cents: int
    shipping_cents: int
    tax_cents: int
    total_cents: int
    currency: str
    payment_status: str | None  # latest payment attempt (None = never attempted)
    items: list[OrderLineOut]


class OrderStatusIn(Schema):
    status: str


class MetricsOut(Schema):
    orders_placed: int
    orders_fulfilled: int


class DevChargeIn(Schema):
    """What the shop sends the (dev) gateway when creating a charge."""

    amount: int
    currency: str
    order_id: int


class DevChargeOut(Schema):
    id: str
    client_secret: str


class PaymentOut(Schema):
    payment_id: int
    charge_id: str
    client_secret: str | None
    status: str


class WebhookIn(Schema):
    id: str
    type: str
    data: dict[str, Any] = {}


class WebhookOut(Schema):
    status: str


# --- admin (OIDC) -------------------------------------------------------------


class AdminMeOut(Schema):
    id: int
    name: str
    email: str
    role: str
