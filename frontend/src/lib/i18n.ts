// Shop and admin each own their message map (shop/locale.ts, admin/locale.ts) so neither chunk
// drags the other's strings along; only the selected locale itself is shared here.
import { reactive } from 'vue'

export const LOCALES = ['en', 'fr', 'ar'] as const
export type Locale = (typeof LOCALES)[number]

const RTL_LOCALES: readonly Locale[] = ['ar']

const LOCALE_KEY = 'arvel_locale'

function stored(): Locale {
  const value = localStorage.getItem(LOCALE_KEY)
  return (LOCALES as readonly string[]).includes(value ?? '') ? (value as Locale) : 'en'
}

export const locale = reactive<{ current: Locale }>({ current: stored() })

export function dir(of: Locale = locale.current): 'ltr' | 'rtl' {
  return RTL_LOCALES.includes(of) ? 'rtl' : 'ltr'
}

/** dir on <html> is what makes the app mirror under Arabic — logical properties follow it. */
export function applyDocumentLocale(): void {
  document.documentElement.setAttribute('lang', locale.current)
  document.documentElement.setAttribute('dir', dir())
}

applyDocumentLocale() // at module load, before the app mounts — no LTR flash

export function setLocale(next: Locale): void {
  localStorage.setItem(LOCALE_KEY, next)
  locale.current = next
  // simplest correct refresh: every fetched view re-renders in the new locale, no stale mix
  window.location.reload()
}

export function currentLocale(): Locale {
  return locale.current
}

/** The `messages[locale][key]` indexing is what makes a key missing from any locale a type error. */
export function makeT<M extends Record<Locale, Record<string, string>>>(messages: M) {
  type Key = keyof M['en']
  return function t(key: Key, params?: Record<string, string | number>): string {
    const raw: string = messages[locale.current][key as string]
    if (!params) return raw
    return raw.replace(/\{(\w+)\}/g, (m, name: string) => String(params[name] ?? m))
  }
}
