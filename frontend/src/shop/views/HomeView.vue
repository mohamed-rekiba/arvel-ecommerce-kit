<script setup lang="ts">
import { onMounted, ref } from "vue";
import { type Category, type Product, api } from "../api";
import ProductCard from "../components/ProductCard.vue";

const categories = ref<Category[]>([]);
const products = ref<Product[]>([]);
const loading = ref(true);

onMounted(async () => {
  try {
    const [cats, page] = await Promise.all([api.categories(), api.products({ page: 1 })]);
    categories.value = cats;
    products.value = page.data;
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="home">
    <!-- hero -->
    <section class="hero">
      <div class="hero__copy">
        <span class="hero__ey">Best choice of the year</span>
        <h1>High-End<br />Electronics</h1>
        <p>Full accessories · free next-day delivery on orders over $120.</p>
        <RouterLink class="btn-amber" to="/">Discover now</RouterLink>
      </div>
      <div class="hero__art" aria-hidden="true" />
    </section>

    <!-- service strip -->
    <section class="svc">
      <div class="svc__it"><b>Free Delivery</b><span>orders over $120</span></div>
      <div class="svc__it"><b>Safe Payment</b><span>100% secure</span></div>
      <div class="svc__it"><b>Shop Confidently</b><span>issue? refunded</span></div>
      <div class="svc__it"><b>24/7 Help Center</b><span>dedicated support</span></div>
      <div class="svc__it"><b>Friendly Returns</b><span>30-day guarantee</span></div>
    </section>

    <!-- promo tiles -->
    <section class="promos">
      <div class="promo" style="background:#283D3B"><h3>Smartphone Bestsellers</h3><span class="promo__lk">Shop now →</span></div>
      <div class="promo" style="background:#795663"><h3>30% off Trending Cameras</h3><span class="promo__lk">Shop now →</span></div>
      <div class="promo" style="background:#12324A"><h3>Top Fresh Accessories</h3><span class="promo__lk">Shop now →</span></div>
    </section>

    <!-- top categories (live) -->
    <section class="sec">
      <div class="sec__hd"><h2>Top Categories <b>of the Month</b></h2><RouterLink class="sec__all" to="/">Browse all →</RouterLink></div>
      <div v-if="loading" class="cats"><div v-for="i in 6" :key="i" class="cat skeleton" /></div>
      <div v-else class="cats">
        <RouterLink v-for="c in categories.slice(0, 6)" :key="c.id" class="cat" :to="{ name: 'catalog', query: { category: c.slug } }">
          <span class="cat__thumb" />
          <b>{{ c.translation.name }}</b><span>Shop now</span>
        </RouterLink>
      </div>
    </section>

    <!-- flash deals (live products) -->
    <section class="sec">
      <div class="sec__hd"><h2>Top <b>Flash Deals</b></h2><RouterLink class="sec__all" to="/">View all →</RouterLink></div>
      <div v-if="loading" class="prods"><div v-for="i in 5" :key="i" class="skeleton skeleton--card" /></div>
      <p v-else-if="!products.length" class="empty">No products yet — seed the catalog to see deals here.</p>
      <div v-else class="prods">
        <ProductCard v-for="p in products.slice(0, 10)" :key="p.id" :product="p" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.home { display: flex; flex-direction: column; gap: 34px; }
.btn-amber { display: inline-flex; align-items: center; height: 44px; padding: 0 22px; border-radius: var(--radius-md); background: var(--accent); color: var(--on-accent); font-weight: 700; text-decoration: none; }

.hero { position: relative; border-radius: var(--radius-lg); overflow: hidden; background: linear-gradient(135deg,#011627,#283D3B); color: #fff; min-height: 320px; display: flex; align-items: center; padding: 44px; box-shadow: var(--shadow-2); }
.hero__ey { font-size: 12px; letter-spacing: .14em; text-transform: uppercase; opacity: .85; font-weight: 700; }
.hero h1 { font-size: 48px; line-height: 1.02; margin: 12px 0; font-weight: 800; }
.hero p { opacity: .9; max-width: 360px; margin-bottom: 22px; }
.hero__art { position: absolute; right: 44px; top: 50%; transform: translateY(-50%); width: 210px; height: 250px; border-radius: 26px; background: linear-gradient(160deg,#0A2033,#283D3B); box-shadow: 0 20px 50px rgba(0,0,0,.35); border: 6px solid rgba(217,188,175,.12); }

.svc { display: grid; grid-template-columns: repeat(5,1fr); gap: 10px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 16px; box-shadow: var(--shadow-1); }
.svc__it { padding-left: 16px; border-left: 1px solid var(--border); }
.svc__it:first-child { border-left: 0; }
.svc__it b { font-size: 13px; display: block; }
.svc__it span { font-size: 11.5px; color: var(--text-subtle); }

.promos { display: grid; grid-template-columns: repeat(3,1fr); gap: 16px; }
.promo { border-radius: var(--radius-lg); padding: 24px; color: #fff; min-height: 140px; display: flex; flex-direction: column; justify-content: center; box-shadow: var(--shadow-2); border: 1px solid rgba(255,255,255,.06); }
.promo h3 { font-size: 21px; font-weight: 800; line-height: 1.15; }
.promo__lk { font-size: 12px; font-weight: 700; margin-top: 12px; }

.sec__hd { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.sec__hd h2 { font-size: 22px; font-weight: 700; }
.sec__hd h2 b { color: var(--accent); }
.sec__all { font-size: 12.5px; font-weight: 700; color: var(--accent); text-decoration: none; }

.cats { display: grid; grid-template-columns: repeat(6,1fr); gap: 12px; }
.cat { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 16px; text-align: center; box-shadow: var(--shadow-1); text-decoration: none; color: var(--text); }
.cat:hover { box-shadow: var(--shadow-2); }
.cat__thumb { width: 64px; height: 64px; border-radius: var(--radius-md); margin: 0 auto 10px; display: block; background: color-mix(in srgb, var(--accent) 10%, var(--surface-2)); }
.cat b { font-size: 13px; display: block; }
.cat span { font-size: 11px; color: var(--text-subtle); }

.prods { display: grid; grid-template-columns: repeat(5,1fr); gap: 16px; }
.empty { color: var(--text-subtle); padding: 30px 0; }

.skeleton { background: var(--surface-2); border-radius: var(--radius-lg); animation: pulse 1.4s ease-in-out infinite; }
.skeleton--card { aspect-ratio: .8; }
.cat.skeleton { height: 120px; }
@keyframes pulse { 50% { opacity: .5; } }

@media (max-width: 1024px) { .cats { grid-template-columns: repeat(3,1fr); } .prods { grid-template-columns: repeat(3,1fr); } }
@media (max-width: 720px) { .svc { grid-template-columns: repeat(2,1fr); } .promos { grid-template-columns: 1fr; } .cats,.prods { grid-template-columns: repeat(2,1fr); } .hero__art { display: none; } .hero h1 { font-size: 36px; } }
</style>
