<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { type Announcement, type Category, api, formatPrice } from "./api";
import { useAuth } from "./auth";
import { useCart } from "./cart";
import { useWishlist } from "./wishlist";
import { theme, toggleTheme } from "../lib/theme";
import { useSettings } from "./settings";
import NewsletterBand from "./components/NewsletterBand.vue";
import MobileNav from "./components/MobileNav.vue";

const { count, state: cartState, refresh } = useCart();
const wishlist = useWishlist();
const auth = useAuth();
const settings = useSettings();
const router = useRouter();
const route = useRoute();

import { LOCALES, locale, setLocale, t } from "./locale";

const cartTotal = computed(() => {
  const cart = cartState.cart;
  if (!cart) return 0;
  return cart.total_cents - (cart.discount_cents ?? 0);
});

// --- scoped search ---
const categories = ref<Category[]>([]);
const searchQ = ref(String(route.query.q ?? ""));
const searchCat = ref("");
function submitSearch() {
  const query: Record<string, string> = {};
  if (searchQ.value.trim()) query.q = searchQ.value.trim();
  if (searchCat.value) query.category = searchCat.value;
  router.push({ name: "catalog", query });
}

// --- collection dropdown ---
const collOpen = ref(false);
const collRef = ref<HTMLElement | null>(null);
function onDocClick(e: MouseEvent) {
  if (collRef.value && !collRef.value.contains(e.target as Node)) collOpen.value = false;
}

// --- announcement bar ---
const announcement = ref<Announcement | null>(null);
const dismissed = ref(false);
const DISMISS_KEY = "arvel_announce_dismissed";
const showAnnounce = computed(() => announcement.value !== null && !dismissed.value);
function dismissAnnounce() {
  if (announcement.value) localStorage.setItem(DISMISS_KEY, announcement.value.code);
  dismissed.value = true;
}

const navOpen = ref(false);
const navTrigger = ref<HTMLButtonElement | null>(null);
function closeNav() {
  navOpen.value = false;
  navTrigger.value?.focus();
}
watch(() => route.fullPath, () => {
  navOpen.value = false;
  collOpen.value = false;
});

// Keying the view by path forces a fresh mount per route, so the PDP re-reads the product cache in setup().
const vtSupported = "startViewTransition" in Document.prototype;

onMounted(() => {
  refresh();
  void settings.load();
  wishlist.refresh();
  document.addEventListener("click", onDocClick);
  void api.categories().then((c) => (categories.value = c)).catch(() => {});
  void api.announcement().then((a) => {
    announcement.value = a;
    dismissed.value = a !== null && localStorage.getItem(DISMISS_KEY) === a.code;
  });
});
onBeforeUnmount(() => document.removeEventListener("click", onDocClick));
</script>

<template>
  <div class="shop">
    <!-- utility topbar -->
    <div class="tb">
      <div class="tb__in">
        <div class="tb__contact">
          <span class="tb__welcome">{{ settings.get("store.welcome") || t("topbar.welcome") }}</span>
          <a :href="`mailto:${settings.get('store.email', 'shop@arvel.test')}`" class="tb__link">{{ settings.get("store.email", "shop@arvel.test") }}</a>
          <span class="tb__link tb__phone" dir="ltr">{{ settings.get("store.phone", "+1 (086) 123-5678") }}</span>
        </div>
        <div class="tb__tools">
          <span class="tb__cur">USD</span>
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
          <button class="tb__theme" @click="toggleTheme" :aria-label="theme === 'dark' ? t('a11y.theme_light') : t('a11y.theme_dark')">
            {{ theme === "dark" ? "☀" : "☾" }}
          </button>
        </div>
      </div>
    </div>

    <!-- main header: logo · scoped search · account · cart -->
    <header class="hd">
      <div class="hd__in">
        <button
          ref="navTrigger"
          class="ic hamburger"
          @click="navOpen = !navOpen"
          :aria-expanded="navOpen"
          aria-controls="mobile-nav-panel"
          :aria-label="t('a11y.menu')"
        >
          <svg v-if="!navOpen" viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
          <svg v-else viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
        <RouterLink to="/" class="brand" :aria-label="t('a11y.home')">
          <span class="brand__name">Arvel<b>Shop</b></span>
          <span class="brand__tag">{{ t("header.tagline") }}</span>
        </RouterLink>

        <form class="search" role="search" @submit.prevent="submitSearch">
          <input
            v-model.trim="searchQ"
            type="search"
            class="search__input"
            :placeholder="t('header.search_ph')"
            :aria-label="t('nav.search')"
          />
          <select v-model="searchCat" class="search__cat" :aria-label="t('header.all_categories')">
            <option value="">{{ t("header.all_categories") }}</option>
            <option v-for="c in categories" :key="c.id" :value="c.slug">{{ c.translation.name }}</option>
          </select>
          <button type="submit" class="search__go">{{ t("header.search") }}</button>
        </form>

        <div class="hd__tools">
          <RouterLink to="/account" class="who">
            <svg viewBox="0 0 24 24" class="who__ic"><circle cx="12" cy="8" r="3.4" /><path d="M5 20a7 7 0 0 1 14 0" /></svg>
            <span class="who__meta">
              <b>{{ auth.state.customer ? t("header.greeting", { name: auth.state.customer.name.split(" ")[0] }) : t("header.guest") }}</b>
              <i>{{ auth.state.customer ? t("account.eyebrow") : t("header.login_register") }}</i>
            </span>
          </RouterLink>
          <RouterLink to="/cart" class="cartw" :aria-label="t('nav.cart')">
            <span class="cartw__ic">
              <svg viewBox="0 0 24 24"><path d="M6 8h12l-1 12H7z" /><path d="M9 8a3 3 0 0 1 6 0" /></svg>
              <span v-if="count" class="n">{{ count }}</span>
            </span>
            <span class="who__meta">
              <b>{{ t("header.your_cart") }}</b>
              <i class="tnum">{{ formatPrice(cartTotal) }}</i>
            </span>
          </RouterLink>
        </div>
      </div>
    </header>

    <!-- charcoal nav -->
    <nav class="nv" :aria-label="t('a11y.primary')">
      <div class="nv__in">
        <div class="nv__links">
          <RouterLink to="/" class="nv__a" exact-active-class="on">{{ t("nav.home") }}</RouterLink>
          <RouterLink :to="{ name: 'catalog' }" class="nv__a" :class="{ on: route.name === 'catalog' }">{{ t("nav.shop") }}</RouterLink>
          <div ref="collRef" class="nv__dd">
            <button class="nv__a nv__dd-btn" :aria-expanded="collOpen" @click="collOpen = !collOpen" @keydown.escape="collOpen = false">
              {{ t("nav.collections") }} <span aria-hidden="true">▾</span>
            </button>
            <div v-if="collOpen" class="nv__menu">
              <RouterLink
                v-for="c in categories"
                :key="c.id"
                class="nv__mi"
                :to="{ name: 'catalog', query: { category: c.slug } }"
              >
                {{ c.translation.name }}
              </RouterLink>
            </div>
          </div>
          <RouterLink to="/deals" class="nv__a" active-class="on">{{ t("nav.deals") }}</RouterLink>
          <RouterLink to="/" class="nv__a">{{ t("nav.about") }}</RouterLink>
        </div>
        <RouterLink to="/deals" class="nv__special">{{ t("nav.special") }}</RouterLink>
      </div>
    </nav>

    <!-- announcement (live coupon) -->
    <div v-if="showAnnounce && announcement" class="ann">
      <p class="ann__txt">
        🎁 {{ t("announce.text") }} <b class="ann__code">{{ announcement.code }}</b>
        <template v-if="announcement.type === 'percent'"> — {{ t("announce.percent", { n: announcement.value }) }}</template>
      </p>
      <button class="ann__x" :aria-label="t('announce.dismiss')" @click="dismissAnnounce">✕</button>
    </div>

    <MobileNav :open="navOpen" :categories="categories" @close="closeNav" />

    <main class="main">
      <RouterView v-slot="{ Component }">
        <component :is="Component" v-if="vtSupported" :key="route.path" />
        <transition v-else name="fade" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </RouterView>
    </main>

    <NewsletterBand />

    <footer class="ft">
      <div class="ft__top">
        <div class="ft__brand">
          <div class="brand__name brand__name--ft">Arvel<b>Shop</b></div>
          <p>{{ t("footer.tagline") }}</p>
        </div>
        <div class="ft__cols">
          <div><h4>{{ t("footer.shop") }}</h4><a>{{ t("footer.new_arrivals") }}</a><a>{{ t("footer.audio") }}</a><a>{{ t("footer.displays") }}</a><a>{{ t("footer.accessories") }}</a></div>
          <div><h4>{{ t("footer.support") }}</h4><a>{{ t("footer.track_order") }}</a><a>{{ t("footer.shipping_returns") }}</a><a>{{ t("footer.contact") }}</a></div>
          <div><h4>{{ t("footer.company") }}</h4><a>{{ t("nav.about") }}</a><a>{{ t("footer.stores") }}</a><a>{{ t("footer.journal") }}</a></div>
        </div>
      </div>
      <div class="ft__base">
        <span>{{ t("footer.copyright") }}</span>
        <span>{{ t("footer.legal") }}</span>
      </div>
    </footer>

    <!-- mobile bottom tab bar (marketplace pattern) -->
    <nav class="tabbar" :aria-label="t('a11y.primary')">
      <RouterLink to="/" class="tabbar__i" exact-active-class="on">
        <svg viewBox="0 0 24 24"><path d="M3 11l9-8 9 8M5 9v11h14V9" /></svg>
        <span>{{ t("nav.home") }}</span>
      </RouterLink>
      <RouterLink :to="{ name: 'catalog' }" class="tabbar__i" :class="{ on: route.name === 'catalog' }">
        <svg viewBox="0 0 24 24"><path d="M4 5h7v7H4zM13 5h7v7h-7zM4 14h7v5H4zM13 14h7v5h-7z" /></svg>
        <span>{{ t("nav.shop") }}</span>
      </RouterLink>
      <RouterLink to="/deals" class="tabbar__i" active-class="on">
        <svg viewBox="0 0 24 24"><path d="M12 3v18M5 8l7-5 7 5M7 21h10" /></svg>
        <span>{{ t("nav.deals") }}</span>
      </RouterLink>
      <RouterLink to="/cart" class="tabbar__i" active-class="on">
        <span class="tabbar__badgewrap">
          <svg viewBox="0 0 24 24"><path d="M6 8h12l-1 12H7z" /><path d="M9 8a3 3 0 0 1 6 0" /></svg>
          <span v-if="count" class="tabbar__n">{{ count }}</span>
        </span>
        <span>{{ t("nav.cart") }}</span>
      </RouterLink>
      <RouterLink to="/account" class="tabbar__i" active-class="on">
        <svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="3.4" /><path d="M5 20a7 7 0 0 1 14 0" /></svg>
        <span>{{ t("nav.account") }}</span>
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.shop { min-height: 100vh; display: flex; flex-direction: column; background: var(--bg); }

/* utility topbar */
.tb { background: var(--surface-2); border-bottom: 1px solid var(--border); font-size: 12px; }
.tb__in { max-width: 1320px; margin: 0 auto; padding: 6px clamp(1rem, 4vw, 2.5rem); display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.tb__contact { display: none; align-items: center; gap: 18px; color: var(--text-muted); }
.tb__welcome { font-weight: 500; }
.tb__link { color: var(--text-muted); text-decoration: none; }
.tb__phone { unicode-bidi: isolate; }
.tb__tools { display: flex; align-items: center; gap: 12px; margin-inline-start: auto; }
.tb__cur { color: var(--text-subtle); font-weight: 600; letter-spacing: .04em; }
.lang { display: flex; gap: 2px; }
.lang__opt { border: 0; background: none; font: inherit; font-size: 11px; font-weight: 700; color: var(--text-muted); padding: 3px 7px; border-radius: var(--radius-full); cursor: pointer; }
.lang__opt.on { background: var(--text); color: var(--bg); }
.tb__theme { border: 0; background: none; font-size: 13px; cursor: pointer; color: var(--text-muted); padding: 2px 4px; }

/* header */
.hd { background: var(--surface); border-bottom: 1px solid var(--border); }
.hd__in { max-width: 1320px; margin: 0 auto; padding: 10px clamp(1rem, 4vw, 2.5rem); display: grid; grid-template-columns: auto auto 1fr auto; grid-template-areas: "menu brand . tools" "search search search search"; align-items: center; gap: 10px clamp(.5rem, 2vw, 2rem); }
.hamburger { grid-area: menu; }
.brand { grid-area: brand; }
.search { grid-area: search; }
.hd__tools { grid-area: tools; }
@media (min-width: 640px) {
  .hd__in { grid-template-areas: none; grid-template-columns: auto auto 1fr auto; padding: 14px clamp(1rem, 4vw, 2.5rem); }
  .hamburger, .brand, .search, .hd__tools { grid-area: auto; }
}
.hamburger { display: grid; }
.ic { width: 44px; height: 44px; border: 0; background: none; place-items: center; color: var(--text); cursor: pointer; }
.ic svg { width: 22px; height: 22px; stroke: currentColor; fill: none; stroke-width: 1.8; }
.brand { text-decoration: none; color: var(--text); display: flex; flex-direction: column; line-height: 1.1; }
.brand__name { font-family: var(--font-display); font-weight: 800; font-size: 22px; letter-spacing: -.01em; }
.brand__name b { color: var(--accent-text); }
.brand__tag { font-size: 10.5px; color: var(--text-subtle); }
.search { display: grid; grid-template-columns: minmax(110px, 1fr) auto auto; border: 2px solid var(--text); border-radius: var(--radius-full); overflow: hidden; background: var(--surface); max-width: 620px; width: 100%; justify-self: center; }
.search__input { border: 0 !important; background: transparent !important; padding: 0 18px; height: 42px; font: inherit; font-size: 14px; min-width: 0; }
.search__input:focus { outline: none; }
.search__cat { border: 0 !important; border-inline-start: 1px solid var(--border) !important; border-radius: 0 !important; background: transparent !important; font-size: 13px; color: var(--text-muted); padding: 0 10px; max-width: 150px; }
.search__go { border: 0; background: var(--accent); color: var(--on-accent); font: inherit; font-size: 13px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; padding: 0 22px; cursor: pointer; }
.search__go:hover { background: var(--accent-hover); }
.hd__tools { display: flex; align-items: center; gap: clamp(.5rem, 2vw, 1.5rem); }
.who, .cartw { display: flex; align-items: center; gap: 10px; text-decoration: none; color: var(--text); }
.who__ic { width: 26px; height: 26px; stroke: currentColor; fill: none; stroke-width: 1.7; }
.who__meta { display: none; flex-direction: column; line-height: 1.25; }
.who__meta b { font-size: 13px; font-weight: 600; }
.who__meta i { font-style: normal; font-size: 11.5px; color: var(--text-muted); }
.cartw__ic { position: relative; display: grid; place-items: center; width: 34px; height: 34px; }
.cartw__ic svg { width: 26px; height: 26px; stroke: currentColor; fill: none; stroke-width: 1.7; }
.n { position: absolute; top: -3px; inset-inline-end: -5px; min-width: 17px; height: 17px; padding: 0 4px; background: var(--accent-bright); color: var(--on-accent-bright); border-radius: var(--radius-full); font-size: 10.5px; font-weight: 800; display: grid; place-items: center; }

/* charcoal nav */
.nv { background: var(--nav-bg); display: none; }
.nv__in { max-width: 1320px; margin: 0 auto; padding: 0 clamp(1rem, 4vw, 2.5rem); display: flex; align-items: stretch; justify-content: space-between; }
.nv__links { display: flex; align-items: stretch; }
.nv__a { display: flex; align-items: center; gap: 6px; padding: 13px 16px; color: var(--nav-text); font-size: 12.5px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; text-decoration: none; border: 0; background: none; font-family: var(--font-text); cursor: pointer; }
.nv__a:hover, .nv__a.on { color: var(--nav-text-hi); }
.nv__a.on { box-shadow: inset 0 -2px 0 var(--nav-active); }
.nv__dd { position: relative; display: flex; }
.nv__menu { position: absolute; top: 100%; inset-inline-start: 0; z-index: var(--z-dropdown); min-width: 230px; background: var(--surface); border: 1px solid var(--border); border-radius: 0 0 var(--radius-md) var(--radius-md); box-shadow: var(--shadow-3); padding: 6px 0; }
.nv__mi { display: block; padding: 9px 18px; font-size: 13.5px; color: var(--text); text-decoration: none; }
.nv__mi:hover { background: var(--surface-2); color: var(--accent-text); }
.nv__special { display: flex; align-items: center; padding: 13px 0; color: var(--nav-active); font-size: 12.5px; font-weight: 800; letter-spacing: .07em; text-transform: uppercase; text-decoration: none; }

/* announcement */
.ann { background: var(--accent-bright); color: var(--on-accent-bright); display: flex; align-items: center; justify-content: center; gap: 12px; padding: 8px clamp(1rem, 4vw, 2.5rem); }
.ann__txt { margin: 0; font-size: 13px; font-weight: 600; text-align: center; }
.ann__code { font-family: var(--font-mono); font-weight: 800; letter-spacing: .04em; background: color-mix(in srgb, var(--on-accent-bright) 12%, transparent); padding: 1px 8px; border-radius: var(--radius-sm); }
.ann__x { border: 0; background: none; color: var(--on-accent-bright); font-size: 13px; cursor: pointer; padding: 4px 6px; }

.main { flex: 1; background: var(--canvas); padding-bottom: 64px; }
@media (min-width: 1024px) { .main { padding-bottom: 0; } }

/* bottom tab bar — phones/tablets only */
.tabbar { position: fixed; bottom: 0; inset-inline: 0; z-index: var(--z-header); display: grid; grid-template-columns: repeat(5, 1fr); background: var(--surface); border-top: 1px solid var(--border); padding-bottom: env(safe-area-inset-bottom, 0px); }
.tabbar__i { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 8px 0 6px; font-size: 10.5px; font-weight: 600; color: var(--text-muted); text-decoration: none; }
.tabbar__i svg { width: 22px; height: 22px; stroke: currentColor; fill: none; stroke-width: 1.7; }
.tabbar__i.on { color: var(--accent-text); }
.tabbar__badgewrap { position: relative; display: grid; place-items: center; }
.tabbar__n { position: absolute; top: -4px; inset-inline-end: -8px; min-width: 15px; height: 15px; padding: 0 3px; background: var(--accent-bright); color: var(--on-accent-bright); border-radius: var(--radius-full); font-size: 9.5px; font-weight: 800; display: grid; place-items: center; }
@media (min-width: 1024px) { .tabbar { display: none; } }

/* footer */
.ft { border-top: 1px solid var(--border); background: var(--surface); }
.ft__top { max-width: 1320px; margin: 0 auto; padding: clamp(2.5rem, 5vw, 4rem) clamp(1rem, 4vw, 2.5rem) clamp(1.5rem, 3vw, 2.5rem); display: grid; grid-template-columns: 1fr; gap: 36px; }
.brand__name--ft { font-size: 20px; }
.ft__brand p { color: var(--text-muted); font-size: 14px; max-width: 30ch; line-height: 1.6; margin-top: 10px; }
.ft__cols { display: grid; grid-template-columns: 1fr; gap: 24px; }
.ft__cols h4 { font-size: 11px; text-transform: uppercase; letter-spacing: .14em; color: var(--text-subtle); margin: 0 0 14px; font-weight: 700; }
.ft__cols a { display: block; font-size: 14px; color: var(--text-muted); text-decoration: none; padding: 5px 0; transition: color var(--motion-base); }
.ft__cols a:hover { color: var(--accent-text); }
.ft__base { border-top: 1px solid var(--border); max-width: 1320px; margin: 0 auto; padding: 18px clamp(1rem, 4vw, 2.5rem); display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 12.5px; color: var(--text-subtle); }

@media (min-width: 640px) {
  .who__meta { display: flex; }
}
/* search shares the header row here — drop the category select so input + button fit */
@media (min-width: 640px) and (max-width: 1023.98px) {
  .search__cat { display: none; }
}
@media (min-width: 1024px) {
  .tb__contact { display: flex; }
  .nv { display: block; }
  .hamburger { display: none; }
  .ft__cols { grid-template-columns: repeat(3, 1fr); }
  .ft__top { grid-template-columns: 1.2fr 2fr; }
}
</style>
