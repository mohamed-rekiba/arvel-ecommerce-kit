// Storefront locale — drives the API's Accept-Language (the server projects catalog content
// per locale, whitelisted to en/fr/ar), the static chrome strings below, and the document
// direction (Arabic renders right-to-left). The choice persists across navigation and reloads.
import { reactive } from "vue";

export const LOCALES = ["en", "fr", "ar"] as const;
export type Locale = (typeof LOCALES)[number];

const RTL_LOCALES: readonly Locale[] = ["ar"];

const LOCALE_KEY = "arvel_locale";

function stored(): Locale {
  const value = localStorage.getItem(LOCALE_KEY);
  return (LOCALES as readonly string[]).includes(value ?? "") ? (value as Locale) : "en";
}

export const locale = reactive<{ current: Locale }>({ current: stored() });

export function dir(of: Locale = locale.current): "ltr" | "rtl" {
  return RTL_LOCALES.includes(of) ? "rtl" : "ltr";
}

/** Reflect the active locale on <html> — lang for a11y/fonts, dir so the whole storefront
 *  mirrors under Arabic (flex/grid/logical properties follow the document direction). */
export function applyDocumentLocale(): void {
  document.documentElement.setAttribute("lang", locale.current);
  document.documentElement.setAttribute("dir", dir());
}

applyDocumentLocale(); // at module load, before the app mounts — no LTR flash

export function setLocale(next: Locale): void {
  localStorage.setItem(LOCALE_KEY, next);
  locale.current = next;
  // simplest correct refresh: every fetched view re-renders in the new locale, no stale mix
  window.location.reload();
}

export function currentLocale(): Locale {
  return locale.current;
}

// --- static chrome strings (catalog CONTENT comes translated from the API) ----------------------
const MESSAGES = {
  en: {
    "nav.shop": "Shop",
    "nav.collections": "Collections",
    "nav.about": "About",
    "nav.search": "Search",
    "nav.account": "Account",
    "nav.cart": "Cart",
    "cart.title": "Your cart",
    "cart.empty": "Your cart is empty.",
    "cart.checkout": "Checkout",
    "checkout.title": "Checkout",
    "checkout.place": "Place order",
    "checkout.subtotal": "Subtotal",
    "catalog.eyebrow": "Shop",
    "catalog.categories": "Categories",
    "catalog.all": "All products",
    "catalog.one": "product",
    "catalog.many": "products",
    "sort.featured": "Featured",
    "sort.price_asc": "Price: low to high",
    "sort.price_desc": "Price: high to low",
    "sort.newest": "Newest",
    "sort.name": "Name",
    "card.add": "Add to bag",
    "card.adding": "Adding…",
    "card.soldout": "Sold out",
    "footer.tagline": "Considered electronics. Designed to disappear into your life.",
  },
  fr: {
    "nav.shop": "Boutique",
    "nav.collections": "Collections",
    "nav.about": "À propos",
    "nav.search": "Rechercher",
    "nav.account": "Compte",
    "nav.cart": "Panier",
    "cart.title": "Votre panier",
    "cart.empty": "Votre panier est vide.",
    "cart.checkout": "Passer à la caisse",
    "checkout.title": "Paiement",
    "checkout.place": "Passer la commande",
    "checkout.subtotal": "Sous-total",
    "catalog.eyebrow": "Boutique",
    "catalog.categories": "Catégories",
    "catalog.all": "Tous les produits",
    "catalog.one": "produit",
    "catalog.many": "produits",
    "sort.featured": "En vedette",
    "sort.price_asc": "Prix : croissant",
    "sort.price_desc": "Prix : décroissant",
    "sort.newest": "Nouveautés",
    "sort.name": "Nom",
    "card.add": "Ajouter au panier",
    "card.adding": "Ajout…",
    "card.soldout": "Épuisé",
    "footer.tagline": "De l'électronique pensée pour s'effacer dans votre quotidien.",
  },
  ar: {
    "nav.shop": "المتجر",
    "nav.collections": "التشكيلات",
    "nav.about": "من نحن",
    "nav.search": "بحث",
    "nav.account": "الحساب",
    "nav.cart": "السلة",
    "cart.title": "سلة التسوق",
    "cart.empty": "سلة التسوق فارغة.",
    "cart.checkout": "إتمام الشراء",
    "checkout.title": "الدفع",
    "checkout.place": "تأكيد الطلب",
    "checkout.subtotal": "المجموع الفرعي",
    "catalog.eyebrow": "المتجر",
    "catalog.categories": "الفئات",
    "catalog.all": "كل المنتجات",
    "catalog.one": "منتج",
    "catalog.many": "منتجات",
    "sort.featured": "مميز",
    "sort.price_asc": "السعر: من الأقل إلى الأعلى",
    "sort.price_desc": "السعر: من الأعلى إلى الأقل",
    "sort.newest": "الأحدث",
    "sort.name": "الاسم",
    "card.add": "أضِف إلى السلة",
    "card.adding": "جارٍ الإضافة…",
    "card.soldout": "نفدت الكمية",
    "footer.tagline": "إلكترونيات مدروسة، صُممت لتندمج في حياتك.",
  },
} as const satisfies Record<Locale, Record<string, string>>;

export type MessageKey = keyof (typeof MESSAGES)["en"];

export function t(key: MessageKey): string {
  return MESSAGES[locale.current][key];
}
