<script setup lang="ts">
// The BestShop home: hero carousel (admin-managed banners) → trust strip → popular categories →
// Deals of the Day (countdown flash sales) → promo grid → Featured Products. Every section
// handles its empty state (no banners → static slide; no deals → section hides).
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { type Banner, type Category, type Deal, type Product, api } from "../api";
import { cacheCategories, cacheList, cacheProducts, getCachedCategories, getCachedList } from "../product-cache";
import DealCard from "../components/DealCard.vue";
import ProductCard from "../components/ProductCard.vue";
import { t } from "../locale";

const cachedProducts = getCachedList("home");
const categories = ref<Category[]>(getCachedCategories() ?? []);
const featured = ref<Product[]>(cachedProducts ?? []);
const deals = ref<Deal[]>([]);
const banners = ref<Banner[]>([]);
const loading = ref(cachedProducts === null);

// --- hero carousel -------------------------------------------------------------------------
const slide = ref(0);
const slides = computed<Banner[]>(() =>
  banners.value.length
    ? banners.value
    : [
        {
          id: 0,
          title: t("home.fallback_title"),
          subtitle: t("home.fallback_sub"),
          chip: null,
          cta_label: t("home.explore"),
          cta_to: "/catalog",
          image_url: null,
          mobile_image_url: null,
        },
      ],
);
function nextSlide(step: number) {
  slide.value = (slide.value + step + slides.value.length) % slides.value.length;
}
let auto: ReturnType<typeof setInterval> | null = null;
function startAuto() {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduced && slides.value.length > 1) auto = setInterval(() => nextSlide(1), 6000);
}
function stopAuto() {
  if (auto) clearInterval(auto);
  auto = null;
}

onMounted(async () => {
  try {
    const [cats, page, dealList, bannerList] = await Promise.all([
      api.categories(),
      api.products({ featured: true }),
      api.deals(),
      api.banners(),
    ]);
    categories.value = cats;
    cacheCategories(cats);
    featured.value = page.data;
    cacheProducts(page.data);
    cacheList("home", page.data);
    deals.value = dealList;
    banners.value = bannerList;
    startAuto();
  } finally {
    loading.value = false;
  }
});
onBeforeUnmount(stopAuto);

const TRUST = [
  { icon: "🚚", title: "home.trust1", sub: "home.trust1_sub" },
  { icon: "💰", title: "home.trust2", sub: "home.trust2_sub" },
  { icon: "🔒", title: "home.trust3", sub: "home.trust3_sub" },
  { icon: "🎧", title: "home.trust4", sub: "home.trust4_sub" },
  { icon: "🛡", title: "home.trust5", sub: "home.trust5_sub" },
] as const;

const maxDealPct = computed(() =>
  deals.value.reduce((max, d) => Math.max(max, d.percent_off), 0),
);
</script>

<template>
  <div class="home">
    <!-- hero carousel -->
    <section
      class="hero wrap"
      aria-roledescription="carousel"
      :aria-label="t('home.hero_label')"
      @mouseenter="stopAuto"
      @mouseleave="startAuto"
    >
      <div class="hero__frame">
        <transition name="fade" mode="out-in">
          <div :key="slides[slide].id" class="hero__slide" :class="{ 'hero__slide--bare': !slides[slide].image_url }">
            <div class="hero__copy">
              <span v-if="slides[slide].chip" class="hero__chip">{{ slides[slide].chip }}</span>
              <h1>{{ slides[slide].title }}</h1>
              <p v-if="slides[slide].subtitle">{{ slides[slide].subtitle }}</p>
              <RouterLink class="hero__cta" :to="slides[slide].cta_to">
                {{ slides[slide].cta_label || t("home.explore") }}
              </RouterLink>
            </div>
            <img
              v-if="slides[slide].image_url"
              class="hero__img"
              :src="slides[slide].image_url ?? undefined"
              :alt="slides[slide].title"
            />
          </div>
        </transition>
        <button v-if="slides.length > 1" class="hero__nav hero__nav--prev" :aria-label="t('catalog.prev')" @click="nextSlide(-1)">‹</button>
        <button v-if="slides.length > 1" class="hero__nav hero__nav--next" :aria-label="t('catalog.next')" @click="nextSlide(1)">›</button>
        <div v-if="slides.length > 1" class="hero__dots" role="tablist">
          <button
            v-for="(s, i) in slides"
            :key="s.id"
            class="hero__dot"
            :class="{ on: i === slide }"
            role="tab"
            :aria-selected="i === slide"
            :aria-label="`${i + 1} / ${slides.length}`"
            @click="slide = i"
          />
        </div>
      </div>
    </section>

    <!-- trust strip -->
    <section class="wrap">
      <ul class="trust">
        <li v-for="item in TRUST" :key="item.title" class="trust__cell">
          <span class="trust__ic" aria-hidden="true">{{ item.icon }}</span>
          <span class="trust__meta"><b>{{ t(item.title) }}</b><i>{{ t(item.sub) }}</i></span>
        </li>
      </ul>
    </section>

    <!-- popular categories -->
    <section v-if="categories.length" class="wrap block">
      <h2 class="sect">{{ t("home.popular_categories") }}</h2>
      <div class="cats">
        <RouterLink
          v-for="c in categories.slice(0, 6)"
          :key="c.id"
          class="cat"
          :to="{ name: 'catalog', query: { category: c.slug } }"
        >
          <span class="cat__imgwrap">
            <img v-if="c.image_url" :src="c.image_url" alt="" loading="lazy" />
            <span v-else class="cat__ph" aria-hidden="true" />
          </span>
          <b>{{ c.translation.name }}</b>
        </RouterLink>
      </div>
    </section>

    <!-- deals of the day -->
    <section v-if="deals.length" class="wrap block">
      <h2 class="sect">{{ t("home.deals_of_day") }}</h2>
      <div class="deals">
        <DealCard v-for="d in deals.slice(0, 2)" :key="d.id" :deal="d" />
      </div>
    </section>

    <!-- promo grid -->
    <section class="wrap block">
      <div class="promos">
        <div class="promo promo--a">
          <div><b>{{ t("home.promo1") }}</b><i>{{ t("home.promo1_sub") }}</i></div>
        </div>
        <RouterLink to="/deals" class="promo promo--campaign">
          <span class="promo__chip" v-if="maxDealPct">{{ t("home.upto", { n: maxDealPct }) }}</span>
          <b>{{ t("home.campaign") }}</b>
          <i>{{ t("home.campaign_sub") }}</i>
          <span class="promo__cta">{{ t("home.grab_deal") }}</span>
        </RouterLink>
        <div class="promo promo--b">
          <div><b>{{ t("home.promo2") }}</b><i>{{ t("home.promo2_sub") }}</i></div>
        </div>
      </div>
    </section>

    <!-- featured products -->
    <section class="wrap block block--last">
      <h2 class="sect">{{ t("home.featured_products") }}</h2>
      <div v-if="loading" class="grid"><div v-for="i in 4" :key="i" class="sk" /></div>
      <p v-else-if="!featured.length" class="empty">{{ t("home.preparing") }}</p>
      <div v-else class="grid">
        <ProductCard v-for="p in featured.slice(0, 8)" :key="p.id" :product="p" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.wrap { max-width: 1320px; margin: 0 auto; padding-inline: clamp(1rem, 4vw, 2.5rem); }
.block { margin-top: clamp(2.5rem, 6vw, 4.5rem); }
.block--last { padding-bottom: clamp(3rem, 7vw, 5.5rem); }
.sect { font-family: var(--font-display); font-size: clamp(1.25rem, 2.4vw, 1.65rem); font-weight: 800; margin-bottom: clamp(1rem, 2.5vw, 1.75rem); text-align: center; position: relative; }
.sect::after { content: ""; display: block; width: 56px; height: 3px; border-radius: 2px; background: var(--accent-bright); margin: 10px auto 0; }

/* hero */
.hero { padding-top: clamp(1rem, 2.5vw, 1.75rem); }
.hero__frame { position: relative; border-radius: var(--radius-lg); overflow: hidden; background: var(--hero-band); border: 1px solid var(--border); }
.hero__slide { display: grid; grid-template-columns: 1fr; min-height: 320px; }
.hero__copy { display: flex; flex-direction: column; justify-content: center; gap: 14px; padding: clamp(1.5rem, 4.5vw, 3.5rem); z-index: 1; }
.hero__chip { align-self: flex-start; background: var(--accent-bright); color: var(--on-accent-bright); font-size: 11.5px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; padding: 5px 12px; border-radius: var(--radius-full); }
.hero__copy h1 { font-family: var(--font-display); font-size: clamp(1.7rem, 4vw, 3rem); font-weight: 800; text-transform: uppercase; letter-spacing: .01em; line-height: 1.08; color: var(--text); }
.hero__copy p { margin: 0; font-size: 15px; color: var(--text-muted); max-width: 40ch; }
.hero__cta { align-self: flex-start; margin-top: 6px; background: var(--text); color: var(--bg); font-size: 13px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; text-decoration: none; padding: 13px 26px; border-radius: var(--radius-full); }
.hero__cta:hover { opacity: .9; }
.hero__img { width: 100%; height: 100%; object-fit: cover; min-height: 220px; }
.hero__nav { position: absolute; top: 50%; transform: translateY(-50%); width: 40px; height: 40px; border-radius: 999px; border: 0; background: color-mix(in srgb, var(--surface) 85%, transparent); color: var(--text); font-size: 22px; line-height: 1; cursor: pointer; display: grid; place-items: center; box-shadow: var(--shadow-2); z-index: 2; }
.hero__nav--prev { inset-inline-start: 12px; }
.hero__nav--next { inset-inline-end: 12px; }
.hero__dots { position: absolute; bottom: 12px; inset-inline: 0; display: flex; justify-content: center; gap: 7px; z-index: 2; }
.hero__dot { width: 9px; height: 9px; border-radius: 999px; border: 0; padding: 0; background: color-mix(in srgb, var(--text) 25%, transparent); cursor: pointer; }
.hero__dot.on { background: var(--accent-bright); }

/* trust strip */
.trust { list-style: none; margin: clamp(1rem, 2.5vw, 1.5rem) 0 0; padding: 14px clamp(.75rem, 2vw, 1.5rem); display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); }
.trust__cell { display: flex; align-items: center; gap: 10px; }
.trust__ic { font-size: 20px; }
.trust__meta { display: flex; flex-direction: column; line-height: 1.3; }
.trust__meta b { font-size: 12.5px; font-weight: 700; }
.trust__meta i { font-style: normal; font-size: 11px; color: var(--text-subtle); }

/* categories rail */
.cats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.cat { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 16px 10px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); text-decoration: none; color: var(--text); transition: box-shadow var(--motion-base), border-color var(--motion-base); }
.cat:hover { box-shadow: var(--shadow-2); border-color: var(--border-2); }
.cat__imgwrap { width: 92px; height: 92px; border-radius: var(--radius-md); overflow: hidden; background: var(--surface-2); display: grid; place-items: center; }
.cat__imgwrap img { width: 100%; height: 100%; object-fit: cover; }
.cat__ph { width: 100%; height: 100%; background: var(--surface-2); }
.cat b { font-size: 13px; font-weight: 600; text-align: center; }
.cat:hover b { color: var(--accent-text); }

/* deals */
.deals { display: grid; grid-template-columns: 1fr; gap: 16px; }

/* promo grid */
.promos { display: grid; grid-template-columns: 1fr; gap: 14px; }
.promo { border-radius: var(--radius-lg); border: 1px solid var(--border); padding: 24px; min-height: 150px; display: flex; flex-direction: column; justify-content: center; gap: 8px; }
.promo b { font-family: var(--font-display); font-size: 18px; font-weight: 800; display: block; }
.promo i { font-style: normal; font-size: 13px; color: var(--text-muted); display: block; margin-top: 4px; }
.promo--a, .promo--b { background: var(--band); border-color: color-mix(in srgb, var(--border) 55%, var(--band)); }
.promo--campaign { background: var(--nav-bg); color: var(--nav-text-hi); text-decoration: none; align-items: center; text-align: center; gap: 6px; position: relative; }
.promo--campaign b { font-size: clamp(1.4rem, 2.6vw, 2rem); text-transform: uppercase; letter-spacing: .02em; }
.promo--campaign i { color: var(--nav-text); }
.promo__chip { background: var(--accent-bright); color: var(--on-accent-bright); font-size: 12px; font-weight: 800; padding: 4px 12px; border-radius: var(--radius-full); }
.promo__cta { margin-top: 8px; background: var(--accent-bright); color: var(--on-accent-bright); font-size: 12px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; padding: 10px 20px; border-radius: var(--radius-full); }

/* featured grid */
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.sk { aspect-ratio: 3 / 4; border-radius: var(--radius-md); background: var(--surface-2); animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: .55; } }
.empty { color: var(--text-subtle); padding: 32px 0; text-align: center; }

@media (min-width: 640px) {
  .hero__slide { grid-template-columns: 1.05fr .95fr; }
  .trust { grid-template-columns: repeat(3, 1fr); }
  .cats { grid-template-columns: repeat(3, 1fr); }
  .deals { grid-template-columns: repeat(2, 1fr); }
  .grid { grid-template-columns: repeat(3, 1fr); }
}
@media (min-width: 1024px) {
  .trust { grid-template-columns: repeat(5, 1fr); }
  .cats { grid-template-columns: repeat(6, 1fr); }
  .promos { grid-template-columns: 1fr 1.4fr 1fr; }
  .grid { grid-template-columns: repeat(4, 1fr); }
}
</style>
