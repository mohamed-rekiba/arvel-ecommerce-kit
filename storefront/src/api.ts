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

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return (await res.json()) as T;
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
};

export function formatPrice(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(cents / 100);
}
