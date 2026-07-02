// Typed admin API client. Auth is a bearer personal-access token (the RBAC back-office users log in
// with email/password); the token is attached to every request. Keycloak-OIDC login is the production
// alternative — it resolves to the same bearer session via the /admin path (see auth.ts note).

const TOKEN_KEY = "arvel_admin_token";
export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// Every TYPE is an alias of the GENERATED contract (src/api/gen — orval over the arvel OpenAPI
// document). Regenerate after backend changes: make openapi && npm run api:generate.
import type {
  ActivityOut,
  AdminProductOut,
  OrderLineOut,
  OrderOut,
  OrderStatus,
  RoleOut,
  Translate,
  UserOut,
} from "../api/gen/models";

export type Translation = Translate;
export type AdminProduct = AdminProductOut;
export type Role = RoleOut;
export type Activity = ActivityOut;
export type User = UserOut;
export type OrderLine = OrderLineOut;
export type Order = OrderOut;
export type { OrderStatus };

// arvel's LengthAwarePaginator JSON shape (DR-0022), generic over the row type.
export interface Paginated<T> {
  data: T[];
  current_page: number;
  last_page: number;
  per_page: number;
  total: number;
}

// The order state machine (mirrors app/enums.py ORDER_TRANSITIONS) — which status a given one can move to.
export const ORDER_TRANSITIONS: Record<OrderStatus, OrderStatus[]> = {
  pending: ["paid", "cancelled"],
  paid: ["shipped", "cancelled"],
  shipped: ["delivered"],
  delivered: [],
  cancelled: [],
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const t = token.get();
  if (t) headers["Authorization"] = `Bearer ${t}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new ApiError(res.status, `API ${res.status} for ${method} ${path}`);
  return (await res.json()) as T;
}

export const api = {
  async login(email: string, password: string): Promise<string> {
    const res = await request<{ token: string }>("POST", "/login", { email, password });
    token.set(res.token);
    return res.token;
  },
  me: () => request<User>("GET", "/user"),
  products: (page = 1) => request<Paginated<AdminProduct>>("GET", `/admin/products?page=${page}`),
  createProduct: (body: { category_id: number; name: string; price_cents: number; description?: string }) =>
    request<AdminProduct>("POST", "/admin/products", body),
  updateProduct: (id: number, body: { name?: string; price_cents?: number; status?: string }) =>
    request<AdminProduct>("PUT", `/admin/products/${id}`, body),
  deleteProduct: (id: number) => request<{ message: string }>("DELETE", `/admin/products/${id}`),
  roles: () => request<Role[]>("GET", "/admin/roles"),
  assignRole: (userId: number, role: string) =>
    request<{ user_id: number; roles: string[] }>("POST", `/admin/users/${userId}/roles`, { role }),
  audit: () => request<Activity[]>("GET", "/admin/audit"),
  orders: () => request<Order[]>("GET", "/admin/orders"),
  updateOrderStatus: (id: number, status: string) =>
    request<Order>("POST", `/admin/orders/${id}/status`, { status }),
};

export function name(p: AdminProduct): string {
  return p.translations.find((t) => t.locale === "en")?.name ?? p.translations[0]?.name ?? p.slug;
}

export function formatPrice(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(cents / 100);
}
