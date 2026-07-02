<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuth } from "./auth";
import { theme, toggleTheme } from "../lib/theme";
import { LOCALES, locale, setLocale } from "../lib/i18n";
import { t } from "./locale";

const { state, restore, logout } = useAuth();
const router = useRouter();
onMounted(restore);

const initial = computed(() => (state.user?.name ?? state.user?.email ?? "?").charAt(0).toUpperCase());

function signOut() {
  logout();
  router.push("/admin/login");
}
</script>

<template>
  <div class="console">
    <aside class="side">
      <div class="brand"><span class="mk">A</span>Arvel Console</div>
      <div class="store">Odama Electronics Store</div>

      <p class="lbl">{{ t("nav.menu") }}</p>
      <nav>
        <RouterLink to="/admin/dashboard" class="item"><svg viewBox="0 0 24 24" class="ic"><path d="M4 13h6V4H4zM14 20h6V4h-6zM4 20h6v-5H4z"/></svg>{{ t("nav.dashboard") }}</RouterLink>
        <RouterLink to="/admin/orders" class="item"><svg viewBox="0 0 24 24" class="ic"><path d="M6 2l1.5 3h9L18 2M4 7h16l-1.5 12H5.5z"/></svg>{{ t("nav.orders") }}</RouterLink>
        <RouterLink to="/admin/users" class="item" active-class="on"><svg viewBox="0 0 24 24" class="ic"><circle cx="12" cy="8" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>{{ t("nav.users") }}</RouterLink>
      </nav>

      <p class="lbl">{{ t("nav.catalog") }}</p>
      <nav>
        <RouterLink to="/admin/products" class="item"><svg viewBox="0 0 24 24" class="ic"><path d="M3 7l9-4 9 4-9 4z"/><path d="M3 7v10l9 4 9-4V7"/></svg>{{ t("nav.products") }}</RouterLink>
        <RouterLink to="/admin/categories" class="item" active-class="on"><svg viewBox="0 0 24 24" class="ic"><path d="M4 5h7v7H4zM13 5h7v7h-7zM4 14h7v5H4zM13 14h7v5h-7z"/></svg>{{ t("nav.categories") }}</RouterLink>
        <RouterLink to="/admin/reviews" class="item" active-class="on"><svg viewBox="0 0 24 24" class="ic"><path d="M12 3l2.5 5.5 6 .6-4.5 4 1.3 5.9L12 16l-5.3 3 1.3-5.9-4.5-4 6-.6z"/></svg>{{ t("nav.reviews") }}</RouterLink>
      <RouterLink to="/admin/vendors" class="item" active-class="on"><svg viewBox="0 0 24 24" class="ic"><path d="M4 7l8-4 8 4v10l-8 4-8-4z"/><path d="M4 7l8 4 8-4M12 11v10"/></svg>{{ t("nav.vendors") }}</RouterLink>
        <span class="item item--soon"><svg viewBox="0 0 24 24" class="ic"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M4 18l5-4 4 3 3-2 4 3"/></svg>{{ t("nav.media") }}<i>{{ t("nav.soon") }}</i></span>
      </nav>

      <p class="lbl">{{ t("nav.system") }}</p>
      <nav>
        <RouterLink to="/admin/roles" class="item"><svg viewBox="0 0 24 24" class="ic"><path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z"/></svg>{{ t("nav.roles") }}</RouterLink>
        <RouterLink to="/admin/audit" class="item"><svg viewBox="0 0 24 24" class="ic"><path d="M8 6h11M8 12h11M8 18h11M3.5 6h.01M3.5 12h.01M3.5 18h.01"/></svg>{{ t("nav.audit") }}</RouterLink>
        <span class="item item--soon"><svg viewBox="0 0 24 24" class="ic"><circle cx="12" cy="12" r="3"/><path d="M4 12a8 8 0 0 1 .5-2.8l-2-1.5 2-3.4 2.3 1"/></svg>{{ t("nav.settings") }}<i>{{ t("nav.soon") }}</i></span>
      </nav>
    </aside>

    <div class="main">
      <div class="top">
        <div class="cmdk">
          <svg viewBox="0 0 24 24" class="ic ic--sm"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/></svg>
          {{ t("nav.search_hint") }}<kbd>⌘K</kbd>
        </div>
        <div class="sp"></div>
        <div class="lang" role="group" :aria-label="t('a11y.language')">
          <button
            v-for="code in LOCALES"
            :key="code"
            class="lang__opt"
            :class="{ on: locale.current === code }"
            :aria-pressed="locale.current === code"
            @click="locale.current !== code && setLocale(code)"
          >
            {{ code.toUpperCase() }}
          </button>
        </div>
        <button class="tico" @click="toggleTheme" :aria-label="theme === 'dark' ? t('a11y.theme_light') : t('a11y.theme_dark')">{{ theme === "dark" ? "☀" : "☾" }}</button>
        <div class="me">
          <div class="av">{{ initial }}</div>
          <div class="me__meta"><b>{{ state.user?.name ?? state.user?.email ?? "…" }}</b><button class="me__out" @click="signOut">{{ t("nav.sign_out") }}</button></div>
        </div>
      </div>
      <div class="content"><RouterView /></div>
    </div>
  </div>
</template>

<style scoped>
.console { display: flex; min-height: 100vh; background: var(--canvas); color: var(--text); }
.ic { width: 19px; height: 19px; stroke: currentColor; fill: none; stroke-width: 1.8; flex: none; }
.ic--sm { width: 16px; height: 16px; }
.side { width: var(--side-w); flex: none; background: var(--side-bg); color: var(--side-text); border-inline-end: 1px solid var(--side-border); position: sticky; top: 0; height: 100vh; overflow-y: auto; }
.brand { display: flex; align-items: center; gap: 10px; padding: 18px 20px 4px; color: #fff; font-family: var(--font-display); font-weight: 800; font-size: 19px; }
.brand .mk { width: 30px; height: 30px; border-radius: 9px; background: var(--accent); display: grid; place-items: center; color: var(--ink-900); font-weight: 800; }
.store { font-size: 11px; opacity: .6; padding: 0 20px 12px; }
.lbl { font-size: 10.5px; text-transform: uppercase; letter-spacing: .12em; opacity: .55; padding: 14px 20px 6px; font-weight: 700; margin: 0; }
.item { display: flex; align-items: center; gap: 12px; padding: 9px 20px; color: var(--side-text); font-size: 13.5px; font-weight: 500; text-decoration: none; position: relative; }
.item:hover { background: var(--side-bg-2); }
.item.router-link-active { background: var(--side-active); color: #fff; }
.item.router-link-active::before { content: ""; position: absolute; inset-inline-start: 0; top: 6px; bottom: 6px; width: 3px; border-start-end-radius: 3px; border-end-end-radius: 3px; background: var(--accent); }
.item--soon { opacity: .5; cursor: default; }
.item--soon i { margin-inline-start: auto; font-style: normal; font-size: 9.5px; text-transform: uppercase; letter-spacing: .08em; background: var(--side-bg-2); padding: 2px 6px; border-radius: 999px; }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.top { height: var(--topbar-h); background: var(--surface); border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 14px; padding: 0 24px; position: sticky; top: 0; z-index: var(--z-header); }
.cmdk { flex: 1; max-width: 520px; display: flex; align-items: center; gap: 10px; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius-md); height: 40px; padding: 0 12px; color: var(--text-subtle); font-size: 13.5px; }
.cmdk kbd { margin-inline-start: auto; background: var(--surface); border: 1px solid var(--border-2); border-radius: 6px; font-size: 11px; padding: 2px 6px; font-family: var(--font-mono); color: var(--text-muted); }
.sp { flex: 1; }
.tico { width: 38px; height: 38px; border-radius: 10px; border: 0; background: transparent; color: var(--text-muted); cursor: pointer; font-size: 16px; }
.tico:hover { background: var(--surface-2); }
.me { display: flex; align-items: center; gap: 10px; padding-inline-start: 12px; border-inline-start: 1px solid var(--border); }
.av { width: 34px; height: 34px; border-radius: 999px; background: linear-gradient(140deg, var(--accent), var(--accent)); color: var(--ink-900); display: grid; place-items: center; font-weight: 700; }
.me__meta { display: flex; flex-direction: column; min-width: 0; }
.me__meta b { font-size: 13px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.me__out { align-self: flex-start; border: 0; background: none; padding: 0; color: var(--accent); font: inherit; font-size: 11px; cursor: pointer; }
.content { padding: 24px; }
@media (max-width: 860px) { .side { width: 64px; } .brand, .store, .lbl, .item span:not(.n), .item i, .me__meta { display: none; } }
.lang { display: flex; gap: 2px; margin-inline-end: 6px; }
.lang__opt { border: 0; background: none; font: inherit; font-size: 11.5px; font-weight: 600; letter-spacing: .06em; color: var(--text-muted); padding: 4px 7px; border-radius: 6px; cursor: pointer; }
.lang__opt.on { background: var(--accent); color: var(--on-accent, #fff); }
</style>
