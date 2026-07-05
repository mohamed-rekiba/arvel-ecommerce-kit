"""API request + response schemas (arvel.Schema = msgspec.Struct).

Request bodies parse into *In schemas; handlers return *Out schemas. Models are always mapped to
these DTOs (never returned raw), so the wire contract is explicit and decoupled from storage shape.
"""

from __future__ import annotations

from typing import Any

from arvel import Schema

from app.enums import (
    CountryCode,
    CouponType,
    Currency,
    OrderStatus,
    PaymentStatus,
    ReviewStatus,
    PaymentMethod,
)

# --- shared / catalog ---


class Translate(Schema):
    """One locale's translatable fields (the value of `translations[locale]`)."""

    name: str
    description: str | None = None
    locale: str = ""


class CategoryOut(Schema):
    id: int
    slug: str
    translation: Translate
    image_url: str | None = None  # derived: a subtree product's thumb (category tiles)


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


class ProductDealOut(Schema):
    """The live flash-sale attached to a product — struck price + countdown material."""

    id: int
    percent_off: int
    deal_price_cents: (
        int  # base price with the deal applied (variant adjustments re-derive)
    )
    ends_at: str  # ISO-8601 — the storefront countdown ticks toward it


class ProductOut(Schema, omit_defaults=True):
    id: int
    slug: str
    translation: Translate  # the active locale's name/description (scope_in_locale)
    rating_avg: float | None
    rating_count: int
    price_cents: int
    currency: str
    status: str
    featured: bool
    created_at: str | None  # ISO — the storefront derives its NEW badge from recency
    deal: ProductDealOut | None
    gallery: list[GalleryImageOut]  # always present (possibly empty)
    category: CategoryOut | None = None
    variants: list[VariantOut] | None = None


class DealOut(Schema):
    """A 'Deals of the Day' entry — the deal plus its product card + sell-through stats."""

    id: int
    percent_off: int
    deal_price_cents: int
    ends_at: str
    available: int  # Σ variant stock
    sold: int  # Σ order-line quantity on paid/shipped/delivered orders
    product: ProductOut


class DealIn(Schema):
    product_id: int
    percent_off: int
    starts_at: str  # ISO-8601
    ends_at: str
    active: bool = True


class DealUpdateIn(Schema):
    percent_off: int | None = None
    starts_at: str | None = None
    ends_at: str | None = None
    active: bool | None = None


class AdminDealOut(Schema):
    id: int
    product_id: int
    product_name: str
    percent_off: int
    starts_at: str | None
    ends_at: str | None
    active: bool
    live: bool  # active AND inside the window right now


class ProductPage(Schema):
    """The catalog listing — arvel's LengthAwarePaginator shape, typed."""

    data: list[ProductOut]
    current_page: int
    last_page: int
    per_page: int
    total: int


# --- admin views (all rows, incl. hidden, each annotated with is_visible) ---


class AdminProductOut(Schema):
    """A product as the admin sees it — every row, ALL translations, and `is_visible` (whether the
    storefront shows it: published ∧ vendor published ∧ category chain published)."""

    id: int
    slug: str
    translations: list[Translate]
    status: str
    published: bool
    featured: bool
    is_visible: bool
    price_cents: int = 0
    currency: str = "USD"
    image_url: str | None = None  # first gallery image's thumb (admin list rows)
    stock: int = 0  # summed across the product's variants
    variant_count: int = 0


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


# --- auth ---


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
    avatar_url: str | None  # the `profile` conversion
    locale: str


class ProfileIn(Schema):
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class ChangePasswordIn(Schema):
    current_password: str
    password: str


class VerifyEmailIn(Schema):
    id: int  # the user the link is for (in the mailed URL); the token is verified against their email
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


# --- RBAC / audit (admin) ---


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
    email: str  # the account being reset (the broker keys the stored token by email)
    token: str
    password: str


# --- cart ---


class AddItemIn(Schema):
    product_variant_id: int
    quantity: int = 1


class UpdateItemIn(Schema):
    quantity: int


class CartLineOut(Schema):
    id: int
    product_variant_id: int
    product_name: str
    variant_name: str
    image_url: str | None  # the product's thumb — cart rows show what's being bought
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class CartOut(Schema, omit_defaults=True):
    id: int | None
    items: list[CartLineOut]
    total_cents: int
    coupon_code: str | None
    discount_cents: int
    cart_token: str | None = None


class ApplyCouponIn(Schema):
    code: str


class CouponIn(Schema):
    code: str
    type: "CouponType"
    value: int
    min_subtotal_cents: int = 0
    usage_limit: int | None = None
    per_customer_limit: int | None = None
    announce: bool = False


class CouponUpdateIn(Schema):
    active: bool | None = None
    usage_limit: int | None = None
    per_customer_limit: int | None = None
    min_subtotal_cents: int | None = None
    announce: bool | None = None


class AdminCouponOut(Schema):
    id: int
    code: str
    type: "CouponType"
    value: int
    min_subtotal_cents: int
    usage_limit: int | None
    per_customer_limit: int | None
    uses: int
    active: bool
    announce: bool
    starts_at: str | None
    ends_at: str | None


class BannerTextIn(Schema):
    title: str
    subtitle: str | None = None
    chip: str | None = None
    cta_label: str | None = None


class BannerIn(Schema):
    translations: dict[
        str, BannerTextIn
    ]  # locale -> copy; locales whitelisted like products
    cta_to: str = "/catalog"
    sort: int = 0
    active: bool = True


class BannerUpdateIn(Schema):
    translations: dict[str, BannerTextIn] | None = None
    cta_to: str | None = None
    sort: int | None = None
    active: bool | None = None


class BannerOut(Schema):
    """One hero slide, already projected to the REQUEST locale (with en fallback)."""

    id: int
    title: str
    subtitle: str | None
    chip: str | None
    cta_label: str | None
    cta_to: str
    image_url: (
        str | None
    )  # the `hero` conversion (mobile variant derivable client-side)
    mobile_image_url: str | None


class AdminBannerOut(Schema):
    id: int
    translations: dict[str, BannerTextIn]
    cta_to: str
    sort: int
    active: bool
    image_url: str | None


class NewsletterIn(Schema):
    email: str


class NewsletterSubscriberOut(Schema):
    id: int
    email: str
    locale: str
    created_at: str | None


class MediaItemOut(Schema):
    """One row of the back-office media library — any stored file with its owner resolved."""

    id: int
    owner_type: str
    owner_id: int
    owner_label: str
    collection: str
    file_name: str
    mime_type: str
    size: int
    url: str
    thumb_url: str | None
    created_at: str | None


class SettingsOut(Schema):
    """The public storefront settings (whitelisted keys only)."""

    values: dict[str, str]


class SettingsIn(Schema):
    values: dict[str, str]


class AnnouncementOut(Schema):
    """The storefront announcement bar — the newest live coupon flagged for announcement."""

    code: str
    type: "CouponType"
    value: int  # percent points or cents, per type


# --- admin products ---


class TranslationFieldsIn(Schema):
    """One locale's content for a product/category."""

    name: str
    description: str | None = None


class ProductIn(Schema):
    category_id: int
    price_cents: int
    translations: dict[
        str, TranslationFieldsIn
    ]  # locale → content; locales are whitelisted


class UpdateProductIn(Schema):
    category_id: int | None = None
    price_cents: int | None = None
    status: str | None = None
    published: bool | None = None
    featured: bool | None = None
    translations: dict[str, TranslationFieldsIn] | None = None


# --- checkout / orders / payments ---


class OrderTimelineOut(Schema):
    """One step of the customer-facing tracking stepper."""

    status: OrderStatus
    at: str | None  # ISO — None for steps not reached yet


class OrderLineOut(Schema):
    product_variant_id: int
    product_name: str
    product_slug: str | None  # links the line back to the product page (None if since-deleted)
    variant_name: str
    image_url: str | None  # resolved at read time via variant→product media
    quantity: int
    unit_price_cents: int


class SavedAddressIn(Schema):
    """Create/update a saved address-book entry (validated at the controller)."""

    name: str
    line1: str
    city: str
    postal_code: str
    country: "CountryCode"
    label: str | None = None
    line2: str | None = None
    phone: str | None = None
    is_default: bool = False


class SavedAddressOut(Schema):
    id: int
    label: str | None
    name: str
    line1: str
    line2: str | None
    city: str
    postal_code: str
    country: "CountryCode"
    phone: str | None
    is_default: bool


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
    signed-in customers) + shipping address — inline, or a saved address-book id (owned), plus
    the payment method (gateway = pay after placing; cod = collect on delivery)."""

    email: str | None = None
    address: AddressIn | None = None
    address_id: int | None = None  # a saved address-book entry (signed-in customers)
    payment_method: "PaymentMethod" = PaymentMethod.GATEWAY


class AddressOut(Schema):
    name: str
    line1: str
    line2: str | None
    city: str
    postal_code: str
    country: CountryCode


class OrderOut(Schema):
    id: int
    status: OrderStatus
    token: str
    contact_email: str
    address: AddressOut
    subtotal_cents: int
    shipping_cents: int
    tax_cents: int
    coupon_code: str | None
    discount_cents: int
    total_cents: int
    currency: Currency
    payment_method: "PaymentMethod"
    payment_status: (
        PaymentStatus | None
    )  # latest payment attempt (None = never attempted)
    items: list[OrderLineOut]
    placed_at: str | None = None  # ISO created_at — the account order cards show it
    timeline: list[OrderTimelineOut] | None = None  # populated on the single-order read


class ReviewIn(Schema):
    rating: int
    body: str
    title: str | None = None


class ReviewOut(Schema):
    id: int
    rating: int
    title: str | None
    body: str
    status: ReviewStatus
    author: str | None
    created_at: str | None


class ReviewListOut(Schema):
    reviews: list[ReviewOut]  # approved only
    mine: ReviewOut | None  # the caller's own review, any status
    rating_count: int
    rating_avg: float | None


class AdminReviewOut(Schema):
    id: int
    product_slug: str
    author: str
    rating: int
    title: str | None
    body: str
    status: ReviewStatus


class OrderStatusIn(Schema):
    status: str


class MetricsOut(Schema):
    orders_placed: int
    orders_fulfilled: int


class AdminProductDetailOut(Schema):
    """Everything the product editor needs in one read."""

    id: int
    slug: str
    translations: list[Translate]
    status: str
    published: bool
    featured: bool
    is_visible: bool
    price_cents: int
    category_id: int
    variants: list["VariantOut"]
    gallery: list["GalleryImageOut"]


class AdminOrderPaymentOut(Schema):
    id: int
    charge_id: str
    amount_cents: int
    status: PaymentStatus
    created_at: str | None


class AdminOrderEventOut(Schema):
    """One line of the order's history (from the activity trail)."""

    description: str
    causer_id: int | None
    properties: dict[str, str]
    created_at: str | None


class AdminOrderCustomerOut(Schema):
    id: int
    name: str
    email: str


class AdminOrderDetailOut(Schema):
    id: int
    status: OrderStatus
    contact_email: str
    address: AddressOut
    subtotal_cents: int
    shipping_cents: int
    tax_cents: int
    coupon_code: str | None
    discount_cents: int
    total_cents: int
    currency: Currency
    payment_method: "PaymentMethod"
    customer: AdminOrderCustomerOut | None  # None = a guest order
    items: list[OrderLineOut]
    payments: list[AdminOrderPaymentOut]
    history: list[AdminOrderEventOut]


class AdminUserOut(Schema):
    id: int
    name: str
    email: str
    email_verified: bool
    roles: list[str]
    avatar_url: str | None = None


class AdminUserPage(Schema):
    data: list[AdminUserOut]
    current_page: int
    last_page: int
    per_page: int
    total: int


class AdminUserDetailOut(Schema):
    id: int
    name: str
    email: str
    email_verified: bool
    roles: list[str]
    orders_count: int
    total_spent_cents: int
    addresses_count: int = 0
    avatar_url: str | None = None


class CategoryIn(Schema):
    translations: dict[str, TranslationFieldsIn]
    parent_id: int | None = None
    published: bool = True


class CategoryUpdateIn(Schema):
    translations: dict[str, TranslationFieldsIn] | None = None
    parent_id: int | None = None
    published: bool | None = None


class AdminVendorOut(Schema):
    id: int
    name: str
    slug: str
    published: bool


class VendorIn(Schema):
    name: str
    published: bool = True


class VendorUpdateIn(Schema):
    name: str | None = None
    published: bool | None = None


class VariantIn(Schema):
    sku: str
    name: str
    price_adjustment_cents: int = 0
    stock: int = 0


class VariantUpdateIn(Schema):
    sku: str | None = None
    name: str | None = None
    price_adjustment_cents: int | None = None


class StockAdjustIn(Schema):
    """Exactly one of ``set`` (absolute) or ``delta`` (shift); ``reason`` lands in the audit log."""

    set: int | None = None
    delta: int | None = None
    reason: str | None = None


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


# --- admin (OIDC) ---


class AdminMeOut(Schema):
    id: int
    name: str
    email: str
    role: str
