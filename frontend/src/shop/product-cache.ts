// A tiny in-memory product cache keyed by slug. The list views (home / catalog) fill it; the PDP reads
// it *synchronously* so it can render the product image on its very first frame. That's what lets the
// View Transition find a morph target on the new page (an async fetch would render the image too late,
// and the card→PDP "container transform" would degrade to a plain fade).
import type { Product } from "./api";

const cache = new Map<string, Product>();

export function cacheProducts(products: Product[]): void {
  for (const p of products) cache.set(p.slug, p);
}

export function getCachedProduct(slug: string): Product | null {
  return cache.get(slug) ?? null;
}
