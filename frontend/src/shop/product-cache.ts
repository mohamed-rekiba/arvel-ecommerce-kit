// In-memory caches that let a view render its product images on the *first frame* — which is what
// gives the View Transition a `view-transition-name` morph target on BOTH directions:
//   • forward (list → PDP): the PDP seeds its product synchronously from `getCachedProduct`.
//   • back (PDP → list): the list seeds its cards synchronously from `getCachedList` (the `:key`
//     remount would otherwise refetch and render the cards a frame too late — no morph target).
// An async fetch always renders too late, so the morph would degrade to a plain fade.
import type { Category, Product } from "./api";

const bySlug = new Map<string, Product>();
const lists = new Map<string, Product[]>();
let categories: Category[] | null = null;

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

export function cacheCategories(cats: Category[]): void {
  categories = cats;
}

export function getCachedCategories(): Category[] | null {
  return categories;
}
