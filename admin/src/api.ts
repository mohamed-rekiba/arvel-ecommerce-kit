// Typed admin API client. Auth is a bearer personal-access token (the RBAC back-office users log in
// with email/password); the token is attached to every request. Keycloak-OIDC login is the production
// alternative — it resolves to the same bearer session via the /admin path (see auth.ts note).

const TOKEN_KEY = "arvel_admin_token";
export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export interface Translation {
  name: string;
  description: string | null;
  locale: string;
}

export interface AdminProduct {
  id: number;
  slug: string;
  translations: Translation[];
  status: string;
  published: boolean;
  is_visible: boolean;
}

export interface Paginated<T> {
  data: T[];
  current_page: number;
  last_page: number;
  per_page: number;
  total: number;
}

export interface Role {
  id: number;
  name: string;
  permissions: string[];
}

export interface Activity {
  id: number;
  description: string;
  event: string | null;
  causer_id: number | null;
  subject_type: string | null;
  subject_id: number | null;
  properties: Record<string, unknown>;
  created_at: string | null;
}

export interface User {
  id: number;
  name: string;
  email: string;
}

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
};

export function name(p: AdminProduct): string {
  return p.translations.find((t) => t.locale === "en")?.name ?? p.translations[0]?.name ?? p.slug;
}

export function formatPrice(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(cents / 100);
}
