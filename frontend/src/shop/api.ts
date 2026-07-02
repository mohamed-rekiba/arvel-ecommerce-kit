// Thin typed client for the arvel REST API (proxied to the arvel server via vite in dev).
// Every TYPE here is an alias of the GENERATED contract (src/api/gen — orval over the arvel
// OpenAPI document); nothing shape-like is hand-written. Regenerate after backend changes:
//   make openapi && npm run api:generate

import { apiFetch } from "../api/http";
import type {
  AddressOut,
  CartLineOut,
  CartOut,
  CategoryOut,
  CheckoutIn,
  GalleryImageOut,
  NotificationOut,
  OrderLineOut,
  OrderOut,
  PaymentOut,
  ProductOut,
  Translate,
  UserOut,
  VariantOut,
} from "../api/gen/models";
import type { CountryCode } from "../api/gen/models";
import type { ReviewListOut, ReviewOut } from "../api/gen/models";

export { ApiError } from "../api/http";
export type { CountryCode, OrderStatus, PaymentStatus } from "../api/gen/models";

export type Variant = VariantOut;
export type Translation = Translate;
export type GalleryImage = GalleryImageOut;
export type Category = CategoryOut;
export type Product = ProductOut;
export type CartLine = CartLineOut;
export type Cart = CartOut;
export type OrderLine = OrderLineOut;
export type Address = AddressOut;
export type CheckoutPayload = CheckoutIn;
export type Payment = PaymentOut;
export type Order = OrderOut;
export type Customer = UserOut;
export type Notification = NotificationOut;
export type Review = ReviewOut;
export type ReviewList = ReviewListOut;

// arvel's LengthAwarePaginator JSON shape (DR-0022) — generic over the row type (the generated
// ProductPage is this, fixed to ProductOut).
export interface Paginated<T> {
  data: T[];
  current_page: number;
  last_page: number;
  per_page: number;
  total: number;
}

// Display labels for the contract's closed CountryCode set (labels aren't part of the API).
export const SHIPPING_COUNTRIES: { code: CountryCode; label: string }[] = [
  { code: "US", label: "United States" },
  { code: "CA", label: "Canada" },
  { code: "GB", label: "United Kingdom" },
  { code: "DE", label: "Germany" },
  { code: "FR", label: "France" },
  { code: "EG", label: "Egypt" },
];

// The guest cart is keyed by an X-Cart-Token the server issues on first write; we persist it.
const CART_TOKEN_KEY = "arvel_cart_token";
const cartToken = {
  get: () => localStorage.getItem(CART_TOKEN_KEY),
  set: (t: string | null | undefined) => {
    if (t) localStorage.setItem(CART_TOKEN_KEY, t);
  },
};

// Guest order receipts: order id → access token, kept so a guest can revisit/pay/cancel their
// own orders (the server issues the token once, at checkout).
const ORDER_TOKENS_KEY = "arvel_order_tokens";
export const orderTokens = {
  all(): Record<string, string> {
    try {
      return JSON.parse(localStorage.getItem(ORDER_TOKENS_KEY) ?? "{}") as Record<string, string>;
    } catch {
      return {};
    }
  },
  get(id: number): string | undefined {
    return orderTokens.all()[String(id)];
  },
  set(id: number, token: string) {
    const all = orderTokens.all();
    all[String(id)] = token;
    localStorage.setItem(ORDER_TOKENS_KEY, JSON.stringify(all));
  },
};

// A signed-in customer holds a bearer personal-access token (Sanctum-style).
const AUTH_TOKEN_KEY = "arvel_auth_token";
export const authToken = {
  get: () => localStorage.getItem(AUTH_TOKEN_KEY),
  set: (t: string) => localStorage.setItem(AUTH_TOKEN_KEY, t),
  clear: () => localStorage.removeItem(AUTH_TOKEN_KEY),
};

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
): Promise<T> {
  // apiFetch (the orval mutator) owns the bearer/cart-token headers + typed error mapping
  return apiFetch<T>(`/api${path}`, {
    method,
    headers: extraHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

const get = <T>(path: string) => request<T>("GET", path);

function withCartToken(cart: Cart): Cart {
  cartToken.set(cart.cart_token);
  return cart;
}

export const api = {
  products(params: { q?: string; category?: string; sort?: string; page?: number } = {}) {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.category) qs.set("category", params.category);
    if (params.sort) qs.set("sort", params.sort);
    if (params.page) qs.set("page", String(params.page));
    const suffix = qs.toString() ? `?${qs}` : "";
    return get<Paginated<Product>>(`/products${suffix}`);
  },
  product(slug: string) {
    return get<Product>(`/products/${slug}`);
  },
  categories() {
    return get<Category[]>(`/categories`);
  },
  async cart() {
    return withCartToken(await get<Cart>(`/cart`));
  },
  async addToCart(product_variant_id: number, quantity = 1) {
    return withCartToken(await request<Cart>("POST", `/cart/items`, { product_variant_id, quantity }));
  },
  async updateCartItem(id: number, quantity: number) {
    return withCartToken(await request<Cart>("PATCH", `/cart/items/${id}`, { quantity }));
  },
  async removeCartItem(id: number) {
    return withCartToken(await request<Cart>("DELETE", `/cart/items/${id}`));
  },
  reviews(slug: string) {
    return request<ReviewList>("GET", `/products/${slug}/reviews`);
  },
  submitReview(slug: string, payload: { rating: number; body: string; title?: string }) {
    return request<Review>("POST", `/products/${slug}/reviews`, payload);
  },
  async applyCoupon(code: string) {
    return withCartToken(await request<Cart>("POST", `/cart/coupon`, { code }));
  },
  async removeCoupon() {
    return withCartToken(await request<Cart>("DELETE", `/cart/coupon`));
  },
  async order(id: number, orderToken?: string) {
    return request<Order>("GET", `/orders/${id}`, undefined, orderToken ? { "X-Order-Token": orderToken } : undefined);
  },
  async pay(id: number, orderToken?: string) {
    return request<Payment>("POST", `/orders/${id}/pay`, undefined, orderToken ? { "X-Order-Token": orderToken } : undefined);
  },
  async cancelOrder(id: number, orderToken?: string) {
    return request<Order>("POST", `/orders/${id}/cancel`, undefined, orderToken ? { "X-Order-Token": orderToken } : undefined);
  },
  async checkout(payload: CheckoutPayload) {
    const order = await request<Order>("POST", `/checkout`, payload);
    localStorage.removeItem(CART_TOKEN_KEY); // the cart was consumed
    orderTokens.set(order.id, order.token); // the receipt — lets a guest revisit/pay/cancel
    return order;
  },
  async register(name: string, email: string, password: string) {
    const res = await request<{ token: string }>("POST", `/register`, { name, email, password });
    authToken.set(res.token);
    localStorage.removeItem(CART_TOKEN_KEY); // any guest cart was merged into the account
    return res.token;
  },
  async login(email: string, password: string) {
    const res = await request<{ token: string }>("POST", `/login`, { email, password });
    authToken.set(res.token);
    localStorage.removeItem(CART_TOKEN_KEY); // any guest cart was merged into the account
    return res.token;
  },
  forgotPassword(email: string) {
    return request<{ message: string }>("POST", `/forgot-password`, { email });
  },
  resetPassword(token: string, password: string) {
    return request<{ message: string }>("POST", `/reset-password`, { token, password });
  },
  verifyEmail(token: string) {
    return request<{ message: string }>("POST", `/email/verify`, { token });
  },
  resendVerification() {
    return request<{ message: string }>("POST", `/email/verification-notification`);
  },
  updateProfile(payload: { name?: string; email?: string; phone?: string }) {
    return request<Customer>("PATCH", `/user`, payload);
  },
  changePassword(current_password: string, password: string) {
    return request<{ message: string }>("PUT", `/user/password`, { current_password, password });
  },
  me() {
    return get<Customer>(`/user`);
  },
  myOrders() {
    return get<Order[]>(`/orders`);
  },
  notifications() {
    return get<Notification[]>(`/notifications`);
  },
  markNotificationsRead() {
    return request<{ message: string }>("POST", `/notifications/read`);
  },
  wishlist() {
    return get<Product[]>(`/wishlist`);
  },
  toggleWishlist(productId: number) {
    return request<{ saved: boolean }>("POST", `/wishlist/${productId}`);
  },
  async logout() {
    try {
      await request("POST", `/logout`);
    } finally {
      authToken.clear();
    }
  },
};

export function formatPrice(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(cents / 100);
}
