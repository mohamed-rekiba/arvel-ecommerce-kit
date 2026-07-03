// In-memory caches that let a view render its content synchronously on the *first frame* of a
// remount, instead of an empty/loading state that fills in a beat later:
//   • forward (list → PDP): the PDP seeds its product synchronously from `getCachedProduct`.
//   • back (PDP → list): the list seeds its cards synchronously from `getCachedList` (the `:key`
//     remount would otherwise refetch and render a frame too late).
// This isn't just perceived performance — it's correctness. A section that renders late (e.g. a
// `v-if` block that pops in once its fetch resolves) changes page height AFTER vue-router has
// already applied a restored scroll position, so returning "back" to a spot lower on the page
// lands short. Seeding from cache keeps the layout stable at the moment scroll restoration runs.
import type { Banner, Category, Deal, Product } from "./api";

const bySlug = new Map<string, Product>();
const lists = new Map<string, Product[]>();
let categories: Category[] | null = null;
let deals: Deal[] | null = null;
let banners: Banner[] | null = null;

export function cacheProducts(products: Product[]): void {
  for (const p of products) bySlug.set(p.slug, p);
}

export function getCachedProduct(slug: string): Product | null {
  return bySlug.get(slug) ?? null;
}

// A whole list payload, keyed by the caller (e.g. "home" or a catalog query signature), so the list
// view can repaint its exact card set synchronously on remount.
export function cacheList(key: string, products: Product[]): void {
  lists.set(key, products);
}

export function getCachedList(key: string): Product[] | null {
  return lists.get(key) ?? null;
}

// Pagination meta (total/last_page) for a cached list — CatalogView's page nav is `v-if
// last_page > 1`, so without this it starts absent (lastPage defaults to 1) and pops in once
// the refetch resolves, late enough to throw off scroll restoration the same way an uncached
// list would. Keyed identically to cacheList/getCachedList.
const listMeta = new Map<string, { total: number; lastPage: number }>();

export function cacheListMeta(key: string, meta: { total: number; lastPage: number }): void {
  listMeta.set(key, meta);
}

export function getCachedListMeta(key: string): { total: number; lastPage: number } | null {
  return listMeta.get(key) ?? null;
}

export function cacheCategories(cats: Category[]): void {
  categories = cats;
}

export function getCachedCategories(): Category[] | null {
  return categories;
}

// Home re-fetches deals/banners on every mount (they can change independently of the
// product/category lists) — but an uncached async gap here is exactly what breaks scroll
// restoration on the way back from a product: the "Deals of the day" section (v-if'd on a
// non-empty list) doesn't reserve space, so it pops in and pushes the rest of the page down
// a beat after scrollBehavior already applied the saved position. Seeding from the last
// fetch closes that gap; onMounted still refetches to keep them current.
export function cacheDeals(list: Deal[]): void {
  deals = list;
}

export function getCachedDeals(): Deal[] | null {
  return deals;
}

export function cacheBanners(list: Banner[]): void {
  banners = list;
}

export function getCachedBanners(): Banner[] | null {
  return banners;
}
