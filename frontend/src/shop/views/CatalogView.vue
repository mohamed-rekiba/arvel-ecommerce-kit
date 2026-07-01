<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { type Paginated, type Product, api } from "../api";
import ProductCard from "../components/ProductCard.vue";

const products = ref<Product[]>([]);
const page = ref(1);
const lastPage = ref(1);
const total = ref(0);
const query = ref("");
const status = ref<"idle" | "loading" | "error" | "ready">("idle");

async function load() {
  status.value = "loading";
  try {
    const res: Paginated<Product> = await api.products({ q: query.value || undefined, page: page.value });
    products.value = res.data;
    lastPage.value = res.last_page;
    total.value = res.total;
    status.value = "ready";
  } catch {
    status.value = "error";
  }
}

onMounted(load);
watch(page, load);

let debounce: ReturnType<typeof setTimeout>;
watch(query, () => {
  clearTimeout(debounce);
  debounce = setTimeout(() => {
    page.value = 1;
    load();
  }, 250);
});
</script>

<template>
  <section class="hero">
    <div class="hero__inner">
      <p class="eyebrow">Arvel Shop — Collection {{ new Date().getFullYear() }}</p>
      <h1 class="hero__title">Considered goods,<br /><em>calmly presented.</em></h1>
      <p class="hero__sub">
        A reference storefront built on the arvel framework — where the product and the type do the work.
      </p>
    </div>
  </section>

  <main class="catalog">
    <div class="catalog__bar">
      <p class="catalog__count">
        <span v-if="status === 'ready'">{{ total }} {{ total === 1 ? "product" : "products" }}</span>
        <span v-else>&nbsp;</span>
      </p>
      <label class="search">
        <svg class="search__icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2" />
          <line x1="16.5" y1="16.5" x2="21" y2="21" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        </svg>
        <span class="visually-hidden">Search products</span>
        <input v-model="query" type="search" placeholder="Search the collection" />
      </label>
    </div>

    <div v-if="status === 'loading'" class="grid" aria-busy="true">
      <div v-for="n in 8" :key="n" class="skeleton" />
    </div>

    <div v-else-if="status === 'error'" class="state" role="alert">
      <p>We couldn't load the collection.</p>
      <button class="btn" @click="load">Try again</button>
    </div>

    <div v-else-if="products.length === 0" class="state">
      <p>Nothing matches “{{ query }}”.</p>
      <button v-if="query" class="btn" @click="query = ''">Clear search</button>
    </div>

    <template v-else>
      <div class="grid">
        <ProductCard v-for="p in products" :key="p.id" :product="p" />
      </div>
      <nav v-if="lastPage > 1" class="pager" aria-label="Pagination">
        <button class="btn" :disabled="page <= 1" @click="page--">Previous</button>
        <span class="pager__label">Page {{ page }} of {{ lastPage }}</span>
        <button class="btn" :disabled="page >= lastPage" @click="page++">Next</button>
      </nav>
    </template>
  </main>
</template>

<style scoped>
.hero { border-bottom: 1px solid var(--color-border); }
.hero__inner { max-width: var(--container-max); margin: 0 auto; padding: var(--space-20) var(--container-pad) var(--space-16); }
.hero__title { font-size: clamp(2.5rem, 7vw, var(--text-5xl)); margin: var(--space-4) 0 var(--space-5); max-width: 16ch; }
.hero__title em { font-style: italic; color: var(--color-accent); }
.hero__sub { color: var(--color-text-muted); font-size: var(--text-lg); max-width: 46ch; line-height: var(--leading-snug); }

.catalog { max-width: var(--container-max); margin: 0 auto; padding: var(--space-10) var(--container-pad) 0; }
.catalog__bar { display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); margin-bottom: var(--space-8); flex-wrap: wrap; }
.catalog__count { color: var(--color-text-muted); font-size: var(--text-sm); margin: 0; }
.search { position: relative; display: inline-flex; align-items: center; }
.search__icon { position: absolute; left: var(--space-4); color: var(--color-text-muted); pointer-events: none; }
.search input {
  font: inherit; padding: var(--space-3) var(--space-4) var(--space-3) var(--space-10);
  border: 1px solid var(--color-border-strong); border-radius: var(--radius-full);
  background: var(--color-bg); min-width: 18rem; transition: border-color var(--motion-base) var(--ease);
}
.search input:focus { outline: none; border-color: var(--color-text); }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-8) var(--space-6); }
.skeleton { aspect-ratio: 3 / 4; background: var(--color-surface); border-radius: var(--radius-md); animation: pulse 1.4s var(--ease) infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.55; } }
.state { text-align: center; padding: var(--space-24) 0; color: var(--color-text-muted); }
.state .btn { margin-top: var(--space-4); }
.pager { display: flex; align-items: center; justify-content: center; gap: var(--space-6); margin-top: var(--space-16); }
.pager__label { color: var(--color-text-muted); font-size: var(--text-sm); }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
