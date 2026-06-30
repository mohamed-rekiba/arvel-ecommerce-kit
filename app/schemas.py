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


class CategoryOut(Schema):
    id: int
    name: str
    slug: str


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
    name: str
    slug: str
    description: str | None
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


class MessageOut(Schema):
    message: str


class ForgotPasswordIn(Schema):
    email: str


class ForgotPasswordOut(Schema, omit_defaults=True):
    message: str
    reset_token: str | None = None  # dev convenience; normally emailed


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


class UpdateProductIn(Schema):
    name: str | None = None
    price_cents: int | None = None
    status: str | None = None




# --- checkout / orders / payments ---------------------------------------------


class OrderLineOut(Schema):
    product_variant_id: int
    quantity: int
    unit_price_cents: int


class OrderOut(Schema):
    id: int
    status: str
    total_cents: int
    items: list[OrderLineOut]


class OrderStatusIn(Schema):
    status: str


class MetricsOut(Schema):
    orders_placed: int
    orders_fulfilled: int


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
