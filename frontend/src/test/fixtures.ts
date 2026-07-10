// Typed fixture factories for component tests — build against the generated contract models
// (src/api/gen/models), never `any` (architecture doc §2/§3).
import type {
  AddressOut,
  CartLineOut,
  CartOut,
  OrderLineOut,
  OrderOut,
  ProductOut,
  ShippingMethodOut,
  VariantOut
} from '../api/gen/models'

export function makeVariant(overrides: Partial<VariantOut> = {}): VariantOut {
  return {
    id: 1,
    sku: 'SKU-1',
    name: 'Default',
    price_adjustment_cents: 0,
    stock: 5,
    ...overrides
  }
}

export function makeProduct(overrides: Partial<ProductOut> = {}): ProductOut {
  return {
    id: 1,
    slug: 'test-product',
    translation: { name: 'Test Product', description: null },
    rating_avg: null,
    rating_count: 0,
    price_cents: 2000,
    currency: 'USD',
    status: 'active',
    featured: false,
    created_at: null,
    deal: null,
    gallery: [],
    category: null,
    variants: [makeVariant()],
    ...overrides
  }
}

export function makeCartLine(overrides: Partial<CartLineOut> = {}): CartLineOut {
  return {
    id: 1,
    product_variant_id: 1,
    product_name: 'Test Product',
    variant_name: 'Default',
    image_url: null,
    quantity: 1,
    unit_price_cents: 2000,
    line_total_cents: 2000,
    ...overrides
  }
}

export function makeCart(overrides: Partial<CartOut> = {}): CartOut {
  return {
    id: 1,
    items: [makeCartLine()],
    total_cents: 2000,
    coupon_code: null,
    discount_cents: 0,
    cart_token: 'cart-token-1',
    ...overrides
  }
}

export function makeAddress(overrides: Partial<AddressOut> = {}): AddressOut {
  return {
    name: 'Jane Buyer',
    line1: '1 Market St',
    line2: null,
    city: 'Springfield',
    postal_code: '11111',
    country: 'US',
    ...overrides
  }
}

export function makeOrderLine(overrides: Partial<OrderLineOut> = {}): OrderLineOut {
  return {
    product_variant_id: 1,
    product_name: 'Test Product',
    product_slug: 'test-product',
    variant_name: 'Default',
    image_url: null,
    quantity: 1,
    unit_price_cents: 2000,
    ...overrides
  }
}

export function makeOrder(overrides: Partial<OrderOut> = {}): OrderOut {
  return {
    id: 42,
    status: 'pending',
    token: 'order-token-1',
    contact_email: 'jane@example.com',
    address: makeAddress(),
    subtotal_cents: 2000,
    shipping_cents: 500,
    tax_cents: 100,
    coupon_code: null,
    discount_cents: 0,
    total_cents: 2600,
    currency: 'USD',
    payment_method: 'gateway',
    payment_status: null,
    shipping_method: 'standard',
    tracking_number: null,
    items: [makeOrderLine()],
    ...overrides
  }
}

export function makeShippingMethod(overrides: Partial<ShippingMethodOut> = {}): ShippingMethodOut {
  return {
    code: 'standard',
    name: 'Standard',
    rate_cents: 500,
    ...overrides
  }
}
