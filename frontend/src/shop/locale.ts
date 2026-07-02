// Storefront locale — drives the API's Accept-Language (the server projects catalog content
// per locale, whitelisted to en/fr) and the static chrome strings below. The choice persists
// across navigation and reloads.
import { reactive } from "vue";

export const LOCALES = ["en", "fr"] as const;
export type Locale = (typeof LOCALES)[number];

const LOCALE_KEY = "arvel_locale";

function stored(): Locale {
  const value = localStorage.getItem(LOCALE_KEY);
  return (LOCALES as readonly string[]).includes(value ?? "") ? (value as Locale) : "en";
}

export const locale = reactive<{ current: Locale }>({ current: stored() });

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
    "footer.tagline": "De l'électronique pensée pour s'effacer dans votre quotidien.",
  },
} as const satisfies Record<Locale, Record<string, string>>;

export type MessageKey = keyof (typeof MESSAGES)["en"];

export function t(key: MessageKey): string {
  return MESSAGES[locale.current][key];
}
