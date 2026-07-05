// An async fetch always renders a frame too late for the View Transition morph to catch — these
// caches let the PDP and list seed synchronously on first frame, in both nav directions.
import type { Category, Product } from './api'

const bySlug = new Map<string, Product>()
const lists = new Map<string, Product[]>()
let categories: Category[] | null = null

export function cacheProducts(products: Product[]): void {
  for (const p of products) bySlug.set(p.slug, p)
}

export function getCachedProduct(slug: string): Product | null {
  return bySlug.get(slug) ?? null
}

export function cacheList(key: string, products: Product[]): void {
  lists.set(key, products)
}

export function getCachedList(key: string): Product[] | null {
  return lists.get(key) ?? null
}

export function cacheCategories(cats: Category[]): void {
  categories = cats
}

export function getCachedCategories(): Category[] | null {
  return categories
}
