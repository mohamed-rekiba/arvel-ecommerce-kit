// Thin typed client for the arvel REST API (proxied to the arvel server via vite in dev).
// Mirrors the response shapes from the kit's catalog + cart endpoints (Modules 1 & 4).

export interface Variant {
  id: number;
  sku: string;
  name: string;
  stock: number;
}

// The active-locale name/description (the API projects one locale per Accept-Language).
export interface Translation {
  name: string;
  description: string | null;
  locale: string;
}

export interface GalleryImage {
  id: number;
  url: string;
  thumb_url: string;
  preview_url: string;
}

export interface Category {
  id: number;
  slug: string;
  translation: Translation;
}

export interface Product {
  id: number;
  slug: string;
  translation: Translation;
  price_cents: number;
  currency: string;
  status: string;
  gallery: GalleryImage[];
  category?: Category | null;
  variants?: Variant[] | null;
}

// arvel's LengthAwarePaginator JSON shape (DR-0022).
export interface Paginated<T> {
  data: T[];
  current_page: number;
  last_page: number;
  per_page: number;
  total: number;
}

// --- cart / checkout ----------------------------------------------------------
export interface CartLine {
  id: number;
  product_variant_id: number;
  quantity: number;
  unit_price_cents: number;
  line_total_cents: number;
}

export interface Cart {
  id: number | null;
  items: CartLine[];
  total_cents: number;
  cart_token?: string | null;
}

export interface OrderLine {
  product_variant_id: number;
  quantity: number;
  unit_price_cents: number;
}

export interface Order {
  id: number;
  status: string;
  total_cents: number;
  items: OrderLine[];
}

export interface Customer {
  id: number;
  name: string;
  email: string;
}

// The guest cart is keyed by an X-Cart-Token the server issues on first write; we persist it.
const CART_TOKEN_KEY = "arvel_cart_token";
const cartToken = {
  get: () => localStorage.getItem(CART_TOKEN_KEY),
  set: (t: string | null | undefined) => {
    if (t) localStorage.setItem(CART_TOKEN_KEY, t);
  },
};

// A signed-in customer holds a bearer personal-access token (Sanctum-style).
const AUTH_TOKEN_KEY = "arvel_auth_token";
export const authToken = {
  get: () => localStorage.getItem(AUTH_TOKEN_KEY),
  set: (t: string) => localStorage.setItem(AUTH_TOKEN_KEY, t),
  clear: () => localStorage.removeItem(AUTH_TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const cart = cartToken.get();
  if (cart) headers["X-Cart-Token"] = cart;
  const auth = authToken.get();
  if (auth) headers["Authorization"] = `Bearer ${auth}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new ApiError(res.status, `API ${res.status} for ${method} ${path}`);
  return (await res.json()) as T;
}

const get = <T>(path: string) => request<T>("GET", path);

function withCartToken(cart: Cart): Cart {
  cartToken.set(cart.cart_token);
  return cart;
}

export const api = {
  products(params: { q?: string; category?: string; page?: number } = {}) {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.category) qs.set("category", params.category);
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
  async checkout() {
    const order = await request<Order>("POST", `/checkout`);
    localStorage.removeItem(CART_TOKEN_KEY); // the cart was consumed
    return order;
  },
  async register(name: string, email: string, password: string) {
    const res = await request<{ token: string }>("POST", `/register`, { name, email, password });
    authToken.set(res.token);
    return res.token;
  },
  async login(email: string, password: string) {
    const res = await request<{ token: string }>("POST", `/login`, { email, password });
    authToken.set(res.token);
    return res.token;
  },
  me() {
    return get<Customer>(`/user`);
  },
  myOrders() {
    return get<Order[]>(`/orders`);
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
