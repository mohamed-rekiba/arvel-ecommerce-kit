<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { type Category, type Product, api, formatPrice } from "../api";
import { cacheCategories, cacheList, cacheProducts, getCachedCategories, getCachedList } from "../product-cache";
import ProductCard from "../components/ProductCard.vue";

// seed synchronously from cache so the cards paint on the first frame after a back-nav — that's the
// morph target for the reverse (PDP → home) View Transition. Refresh in the background either way.
const cachedProducts = getCachedList("home");
const categories = ref<Category[]>(getCachedCategories() ?? []);
const products = ref<Product[]>(cachedProducts ?? []);
const loading = ref(cachedProducts === null);

const hero = computed(() => products.value[0] ?? null);
const heroImage = computed(() => hero.value?.gallery[0]?.url ?? hero.value?.gallery[0]?.preview_url ?? null);
const featured = computed(() => products.value.slice(1, 7));
const more = computed(() => products.value.slice(7, 13));

onMounted(async () => {
  try {
    const [cats, page] = await Promise.all([api.categories(), api.products({ page: 1 })]);
    categories.value = cats;
    cacheCategories(cats);
    products.value = page.data;
    cacheProducts(page.data); // lets the PDP paint the image immediately for the forward morph
    cacheList("home", page.data); // …and lets home repaint its cards synchronously on a back-nav
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="home">
    <!-- hero: product as hero -->
    <section class="hero wrap">
      <div class="hero__copy">
        <span class="eyebrow">New — 2026 Collection</span>
        <h1>High-end electronics,<br />quietly considered.</h1>
        <p>Sound, vision and the objects around them — chosen for how they feel, not how loud they shout.</p>
        <RouterLink :to="{ name: 'catalog' }" class="link">Explore the collection <span aria-hidden="true">→</span></RouterLink>
      </div>
      <div class="hero__media">
        <div class="hero__glow" aria-hidden="true" />
        <RouterLink v-if="hero" :to="`/products/${hero.slug}`" class="hero__frame">
          <img v-if="heroImage" :src="heroImage" :alt="hero.translation.name" />
          <div v-else class="hero__ph" aria-hidden="true" />
          <div class="hero__tag">
            <span>{{ hero.translation.name }}</span>
            <b class="tnum">{{ formatPrice(hero.price_cents, hero.currency) }}</b>
          </div>
        </RouterLink>
        <div v-else class="hero__frame hero__frame--empty" />
      </div>
    </section>

    <!-- featured -->
    <section class="wrap block">
      <div class="head">
        <div><span class="eyebrow">Featured</span><h2>New this season</h2></div>
        <RouterLink :to="{ name: 'catalog' }" class="head__link">View all <span aria-hidden="true">→</span></RouterLink>
      </div>
      <div v-if="loading" class="grid"><div v-for="i in 3" :key="i" class="sk" /></div>
      <p v-else-if="!featured.length" class="empty">The collection is being prepared — check back soon.</p>
      <div v-else class="grid"><ProductCard v-for="p in featured" :key="p.id" :product="p" /></div>
    </section>

    <!-- collections: editorial index -->
    <section class="wrap block">
      <div class="head"><div><span class="eyebrow">Collections</span><h2>Explore by category</h2></div></div>
      <div class="coll">
        <RouterLink
          v-for="(c, i) in categories.slice(0, 3)"
          :key="c.id"
          class="tile"
          :to="{ name: 'catalog', query: { category: c.slug } }"
        >
          <span class="tile__idx">{{ String(i + 1).padStart(2, "0") }}</span>
          <div class="tile__foot">
            <h3>{{ c.translation.name }}</h3>
            <span class="tile__go">Discover <span aria-hidden="true">→</span></span>
          </div>
        </RouterLink>
      </div>
    </section>

    <!-- editorial band -->
    <section class="band wrap">
      <div class="band__inner">
        <div>
          <span class="eyebrow" style="color: var(--blush-300)">The Arvel promise</span>
          <h2>Free 30-day returns.<br />Considered, not disposable.</h2>
        </div>
        <RouterLink :to="{ name: 'catalog' }" class="band__cta">Shop the collection →</RouterLink>
      </div>
    </section>

    <!-- more to explore -->
    <section v-if="more.length" class="wrap block">
      <div class="head">
        <div><span class="eyebrow">The rest</span><h2>More to explore</h2></div>
        <RouterLink :to="{ name: 'catalog' }" class="head__link">Browse all <span aria-hidden="true">→</span></RouterLink>
      </div>
      <div class="grid"><ProductCard v-for="p in more" :key="p.id" :product="p" /></div>
    </section>

    <!-- brand statement -->
    <section class="say">
      <p>“The best technology is the kind you stop noticing — it simply works, and then gets out of the way.”</p>
    </section>
  </div>
</template>

<style scoped>
.wrap { max-width: 1280px; margin: 0 auto; padding-left: clamp(1.25rem, 5vw, 3.5rem); padding-right: clamp(1.25rem, 5vw, 3.5rem); }
.eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: .2em; color: var(--accent); font-weight: 600; }
.block { margin-top: clamp(4rem, 9vw, 7.5rem); }

/* hero */
.hero { display: grid; grid-template-columns: 1fr; align-items: center; gap: 2.5rem; padding-top: clamp(2.5rem, 6vw, 5.5rem); }
.hero__copy .eyebrow { display: block; margin-bottom: 22px; }
.hero h1 { font-family: var(--font-display); font-size: clamp(2.6rem, 5.6vw, 4.6rem); line-height: 1.03; letter-spacing: -.025em; font-weight: 700; color: var(--text); }
.hero p { margin: 26px 0 34px; font-size: 17px; line-height: 1.65; color: var(--text-muted); max-width: 42ch; }
.link { font-size: 14px; font-weight: 600; color: var(--accent); text-decoration: none; border-bottom: 1px solid color-mix(in srgb, var(--accent) 40%, transparent); padding-bottom: 3px; transition: border-color var(--motion-base); }
.link span { display: inline-block; transition: transform var(--motion-base); }
.link:hover { border-color: var(--accent); }
.link:hover span { transform: translateX(4px); }
.hero__media { position: relative; }
.hero__glow { position: absolute; inset: -12% -6% -6% 6%; background: radial-gradient(60% 60% at 60% 40%, color-mix(in srgb, var(--accent) 30%, transparent), transparent 70%); filter: blur(30px); z-index: 0; }
.hero__frame { position: relative; z-index: 1; display: block; aspect-ratio: 4 / 5; border-radius: var(--radius-xl); overflow: hidden; background: var(--surface-2); box-shadow: var(--shadow-3); text-decoration: none; }
.hero__frame img { width: 100%; height: 100%; object-fit: cover; transition: transform 1.2s var(--ease-out); }
.hero__frame:hover img { transform: scale(1.04); }
.hero__ph, .hero__frame--empty { width: 100%; height: 100%; aspect-ratio: 4/5; background: linear-gradient(150deg, var(--surface-2), color-mix(in srgb, var(--accent) 10%, var(--surface-2))); }
.hero__tag { position: absolute; left: 18px; bottom: 18px; right: 18px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 16px; border-radius: var(--radius-md); background: color-mix(in srgb, var(--bg) 82%, transparent); backdrop-filter: blur(8px); }
.hero__tag span { font-size: 13px; font-weight: 600; color: var(--text); }
.hero__tag b { font-family: var(--font-display); font-size: 14px; color: var(--text); }

/* section head */
.head { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: clamp(1.75rem, 4vw, 3rem); }
.head .eyebrow { display: block; margin-bottom: 12px; }
.head h2 { font-family: var(--font-display); font-size: clamp(1.6rem, 3vw, 2.4rem); font-weight: 700; letter-spacing: -.02em; color: var(--text); }
.head__link { font-size: 13px; font-weight: 600; color: var(--text-muted); text-decoration: none; white-space: nowrap; }
.head__link:hover { color: var(--accent); }
.head__link span { display: inline-block; transition: transform var(--motion-base); }
.head__link:hover span { transform: translateX(3px); }

/* product grid */
.grid { display: grid; grid-template-columns: 1fr; gap: clamp(1.5rem, 3vw, 2.75rem); }
.empty { color: var(--text-subtle); padding: 40px 0; font-size: 15px; }
.sk { aspect-ratio: 4/5; border-radius: var(--radius-lg); background: var(--surface-2); animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: .55; } }

/* collections — editorial dark tiles, unified tone */
.coll { display: grid; grid-template-columns: 1fr; gap: clamp(1rem, 2vw, 1.5rem); }
.tile { position: relative; aspect-ratio: 16 / 9; border-radius: var(--radius-lg); overflow: hidden; padding: 26px; display: flex; flex-direction: column; justify-content: space-between; text-decoration: none; color: #F3EDE7; background: radial-gradient(120% 90% at 20% 0%, #12283E 0%, #011627 60%); box-shadow: var(--shadow-2); transition: transform var(--motion-slow) var(--ease-out); }
.tile:hover { transform: translateY(-4px); }
.tile::after { content: ""; position: absolute; inset: 0; background: radial-gradient(80% 60% at 90% 100%, color-mix(in srgb, var(--accent) 45%, transparent), transparent 60%); opacity: .5; }
.tile__idx { position: relative; z-index: 1; font-family: var(--font-display); font-size: 13px; letter-spacing: .1em; opacity: .7; }
.tile__foot { position: relative; z-index: 1; }
.tile__foot h3 { font-family: var(--font-display); font-size: clamp(1.4rem, 2.4vw, 2rem); font-weight: 700; letter-spacing: -.02em; margin-bottom: 8px; }
.tile__go { font-size: 12px; font-weight: 600; letter-spacing: .04em; opacity: .85; }
.tile__go span { display: inline-block; transition: transform var(--motion-base); }
.tile:hover .tile__go span { transform: translateX(4px); }

/* brand statement */
.band { margin-top: clamp(4rem, 9vw, 7.5rem); }
.band__inner { background: linear-gradient(120deg, #011627, #283D3B); color: #F3EDE7; border-radius: var(--radius-xl); padding: clamp(2.5rem, 5vw, 4rem); display: flex; align-items: center; justify-content: space-between; gap: 28px; box-shadow: var(--shadow-2); }
.band__inner h2 { font-family: var(--font-display); font-size: clamp(1.6rem, 3vw, 2.4rem); font-weight: 700; letter-spacing: -.02em; line-height: 1.16; margin-top: 10px; }
.band__cta { flex: none; height: 48px; padding: 0 24px; border-radius: var(--radius-full); background: var(--blush-300); color: var(--ink-900); font-weight: 700; display: inline-flex; align-items: center; text-decoration: none; }
.band__cta:hover { opacity: .92; }

.say { margin-top: clamp(4rem, 9vw, 7.5rem); border-top: 1px solid var(--border); }
.say p { max-width: 900px; margin: 0 auto; padding: clamp(3.5rem, 8vw, 6.5rem) clamp(1.25rem, 5vw, 3.5rem); text-align: center; font-family: var(--font-display); font-size: clamp(1.5rem, 3vw, 2.4rem); line-height: 1.35; letter-spacing: -.01em; color: var(--text-muted); font-weight: 600; }

@media (min-width: 640px) { .grid { grid-template-columns: repeat(2, 1fr); } }
@media (min-width: 1024px) {
  .hero { grid-template-columns: 1.02fr .98fr; gap: clamp(2rem, 5vw, 5rem); }
  .grid { grid-template-columns: repeat(3, 1fr); }
  .coll { grid-template-columns: repeat(3, 1fr); }
  .tile { aspect-ratio: 3 / 3.7; }
}
</style>
