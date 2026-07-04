// Keycloak-OIDC login (auth.ts) resolves to this same bearer session, not a separate auth mode.
const TOKEN_KEY = "arvel_admin_token";
export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// Aliases of the generated contract (src/api/gen); regenerate after backend changes with `make openapi && npm run api:generate`.
import type {
  ActivityOut,
  AdminCategoryOut,
  AdminOrderDetailOut,
  AdminReviewOut,
  AdminUserDetailOut,
  AdminUserOut,
  AdminVendorOut,
  CategoryIn,
  CategoryUpdateIn,
  AdminProductDetailOut,
  AdminProductOut,
  GalleryImageOut,
  OrderLineOut,
  OrderOut,
  OrderStatus,
  ProductIn,
  RoleOut,
  StockAdjustIn,
  Translate,
  UpdateProductIn,
  UserOut,
  VariantIn,
  VariantOut,
  VariantUpdateIn,
  VendorIn,
  VendorUpdateIn,
  AdminBannerOut,
  AdminDealOut,
  BannerIn,
  BannerUpdateIn,
  DealIn,
  DealUpdateIn,
  AdminCouponOut,
  CouponIn,
  CouponUpdateIn,
  MediaItemOut,
  NewsletterSubscriberOut,
  SettingsOutValues,
} from "../api/gen/models";

export type Translation = Translate;
export type { Translate };
export type AdminProduct = AdminProductOut;
export type Role = RoleOut;
export type Activity = ActivityOut;
export type User = UserOut;
export type OrderLine = OrderLineOut;
export type Order = OrderOut;
export type ProductDetail = AdminProductDetailOut;
export type AdminCategory = AdminCategoryOut;
export type AdminUser = AdminUserOut;
export type AdminOrderDetail = AdminOrderDetailOut;
export type AdminDeal = AdminDealOut;
export type AdminBanner = AdminBannerOut;
export type AdminReview = AdminReviewOut;
export type AdminUserDetail = AdminUserDetailOut;
export type Vendor = AdminVendorOut;
export type Variant = VariantOut;
export type MediaItem = MediaItemOut;
export type NewsletterSubscriber = NewsletterSubscriberOut;
export type SettingsValues = SettingsOutValues;
export type GalleryImage = GalleryImageOut;
export type { OrderStatus, ProductIn, StockAdjustIn, UpdateProductIn, VariantIn, VariantUpdateIn };

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

// COD orders never pass through "paid" — they ship straight from pending (server can_transition(cod=True)).
export function nextStates(order: { status: OrderStatus; payment_method: Order["payment_method"] }): OrderStatus[] {
  if (order.payment_method === "cod" && order.status === "pending") return ["shipped", "cancelled"];
  return ORDER_TRANSITIONS[order.status] ?? [];
}

export { ApiError } from "../api/http";
import { apiFetch } from "../api/http";

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const t = token.get();
  // the ADMIN bearer overrides the storefront token the shared mutator would attach
  return apiFetch<T>(`/api${path}`, {
    method,
    headers: t ? { Authorization: `Bearer ${t}` } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

async function upload<T>(path: string, form: FormData): Promise<T> {
  const t = token.get();
  return apiFetch<T>(`/api${path}`, {
    method: "POST",
    headers: t ? { Authorization: `Bearer ${t}` } : undefined,
    body: form,
  });
}

export const api = {
  async login(email: string, password: string): Promise<string> {
    const res = await request<{ token: string }>("POST", "/login", { email, password });
    token.set(res.token);
    return res.token;
  },
  me: () => request<User>("GET", "/user"),
  products: (page = 1, archived = false) =>
    request<Paginated<AdminProduct>>("GET", `/admin/products?page=${page}&archived=${archived}`),
  restoreProduct: (id: number) => request<AdminProduct>("POST", `/admin/products/${id}/restore`),
  productDetail: (id: number) => request<AdminProductDetailOut>("GET", `/admin/products/${id}`),
  categories: () =>
    request<Paginated<{ id: number; slug: string; translations: Translate[]; published: boolean }>>(
      "GET",
      "/admin/categories?per_page=100",
    ),
  adminCategories: () => request<Paginated<AdminCategoryOut>>("GET", "/admin/categories?per_page=100"),
  createCategory: (body: CategoryIn) => request<AdminCategoryOut>("POST", "/admin/categories", body),
  updateCategory: (id: number, body: CategoryUpdateIn) =>
    request<AdminCategoryOut>("PUT", `/admin/categories/${id}`, body),
  deleteCategory: (id: number) => request<{ message: string }>("DELETE", `/admin/categories/${id}`),
  vendors: () => request<AdminVendorOut[]>("GET", "/admin/vendors"),
  createVendor: (body: VendorIn) => request<AdminVendorOut>("POST", "/admin/vendors", body),
  updateVendor: (id: number, body: VendorUpdateIn) =>
    request<AdminVendorOut>("PUT", `/admin/vendors/${id}`, body),
  createProduct: (body: ProductIn) => request<AdminProduct>("POST", "/admin/products", body),
  updateProduct: (id: number, body: UpdateProductIn) =>
    request<AdminProduct>("PUT", `/admin/products/${id}`, body),
  deleteProduct: (id: number) => request<{ message: string }>("DELETE", `/admin/products/${id}`),
  variants: (productId: number) => request<VariantOut[]>("GET", `/admin/products/${productId}/variants`),
  createVariant: (productId: number, body: VariantIn) =>
    request<VariantOut>("POST", `/admin/products/${productId}/variants`, body),
  updateVariant: (id: number, body: VariantUpdateIn) =>
    request<VariantOut>("PATCH", `/admin/variants/${id}`, body),
  adjustStock: (id: number, body: StockAdjustIn) =>
    request<VariantOut>("POST", `/admin/variants/${id}/stock`, body),
  deleteVariant: (id: number) => request<{ message: string }>("DELETE", `/admin/variants/${id}`),
  uploadImage: (productId: number, file: File) => {
    const form = new FormData();
    form.append("image", file);
    return upload<GalleryImageOut[]>(`/admin/products/${productId}/image`, form);
  },
  deleteImage: (productId: number, mediaId: number) =>
    request<GalleryImageOut[]>("DELETE", `/admin/products/${productId}/media/${mediaId}`),
  adminCoupons: () => request<AdminCouponOut[]>("GET", "/admin/coupons"),
  createCoupon: (body: CouponIn) => request<AdminCouponOut>("POST", "/admin/coupons", body),
  updateCoupon: (id: number, body: CouponUpdateIn) => request<AdminCouponOut>("PATCH", `/admin/coupons/${id}`, body),
  adminDeals: () => request<AdminDealOut[]>("GET", "/admin/deals"),
  createDeal: (body: DealIn) => request<AdminDealOut>("POST", "/admin/deals", body),
  updateDeal: (id: number, body: DealUpdateIn) => request<AdminDealOut>("PATCH", `/admin/deals/${id}`, body),
  deleteDeal: (id: number) => request<{ status: string }>("DELETE", `/admin/deals/${id}`),
  adminBanners: () => request<AdminBannerOut[]>("GET", "/admin/banners"),
  createBanner: (body: BannerIn) => request<AdminBannerOut>("POST", "/admin/banners", body),
  updateBanner: (id: number, body: BannerUpdateIn) => request<AdminBannerOut>("PATCH", `/admin/banners/${id}`, body),
  deleteBanner: (id: number) => request<{ status: string }>("DELETE", `/admin/banners/${id}`),
  uploadBannerImage: (id: number, file: File) => {
    const form = new FormData();
    form.append("image", file);
    return upload<AdminBannerOut>(`/admin/banners/${id}/image`, form);
  },
  roles: () => request<Role[]>("GET", "/admin/roles"),
  adminUsers: (q = "") => request<Paginated<AdminUserOut>>("GET", `/admin/users?q=${encodeURIComponent(q)}`),
  adminUserDetail: (id: number) => request<AdminUserDetailOut>("GET", `/admin/users/${id}`),
  revokeRole: (userId: number, role: string) =>
    request<{ user_id: number; roles: string[] }>("DELETE", `/admin/users/${userId}/roles/${role}`),
  assignRole: (userId: number, role: string) =>
    request<{ user_id: number; roles: string[] }>("POST", `/admin/users/${userId}/roles`, { role }),
  audit: () => request<Activity[]>("GET", "/admin/audit"),
  adminReviews: (status = "pending") => request<AdminReviewOut[]>("GET", `/admin/reviews?status=${status}`),
  moderateReview: (id: number, decision: "approve" | "reject") =>
    request<AdminReviewOut>("POST", `/admin/reviews/${id}/${decision}`),
  orders: (params: { status?: string; q?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set("status", params.status);
    if (params.q) qs.set("q", params.q);
    return request<Order[]>("GET", `/admin/orders${qs.toString() ? `?${qs}` : ""}`);
  },
  adminMedia: () => request<MediaItemOut[]>("GET", "/admin/media"),
  adminSettings: () => request<{ values: SettingsOutValues }>("GET", "/admin/settings"),
  updateSettings: (values: Record<string, string>) =>
    request<{ values: SettingsOutValues }>("PATCH", "/admin/settings", { values }),
  newsletter: () => request<NewsletterSubscriberOut[]>("GET", "/admin/newsletter"),
  adminOrder: (id: number) => request<AdminOrderDetailOut>("GET", `/admin/orders/${id}`),
  updateOrderStatus: (id: number, status: string) =>
    request<Order>("POST", `/admin/orders/${id}/status`, { status }),
};

export function name(p: AdminProduct): string {
  return p.translations.find((t) => t.locale === "en")?.name ?? p.translations[0]?.name ?? p.slug;
}

export function formatPrice(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(cents / 100);
}
