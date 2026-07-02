// Locale core shared by the storefront and the admin console. Each app owns its own message
// map (shop/locale.ts, admin/locale.ts) so the admin chunk doesn't drag storefront strings
// along (and vice versa); the selected locale itself is one shared, persisted choice.
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

/** Reflect the active locale on <html> — lang for a11y/fonts, dir so the whole app mirrors
 *  under Arabic (flex/grid/logical properties follow the document direction). */
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

/** Build a typed `t()` over a per-app message map. The union indexing (`messages[locale][key]`)
 *  is what makes a key missing from any locale a type error at the call site. */
export function makeT<M extends Record<Locale, Record<string, string>>>(messages: M) {
  type Key = keyof M["en"];
  return function t(key: Key, params?: Record<string, string | number>): string {
    const raw: string = messages[locale.current][key as string];
    if (!params) return raw;
    return raw.replace(/\{(\w+)\}/g, (m, name: string) => String(params[name] ?? m));
  };
}
