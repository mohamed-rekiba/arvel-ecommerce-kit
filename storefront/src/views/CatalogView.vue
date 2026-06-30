<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { type Paginated, type Product, api } from "../api";
import ProductCard from "../components/ProductCard.vue";

const products = ref<Product[]>([]);
const page = ref(1);
const lastPage = ref(1);
const query = ref("");
const status = ref<"idle" | "loading" | "error" | "ready">("idle");

async function load() {
  status.value = "loading";
  try {
    const res: Paginated<Product> = await api.products({ q: query.value || undefined, page: page.value });
    products.value = res.data;
    lastPage.value = res.last_page;
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
  <main class="catalog">
    <header class="catalog__head">
      <h1>Shop</h1>
      <label class="catalog__search">
        <span class="visually-hidden">Search products</span>
        <input v-model="query" type="search" placeholder="Search products…" />
      </label>
    </header>

    <!-- loading -->
    <div v-if="status === 'loading'" class="grid" aria-busy="true">
      <div v-for="n in 8" :key="n" class="skeleton" />
    </div>

    <!-- error -->
    <div v-else-if="status === 'error'" class="state" role="alert">
      <p>We couldn't load products.</p>
      <button class="btn" @click="load">Try again</button>
    </div>

    <!-- empty -->
    <div v-else-if="products.length === 0" class="state">
      <p>No products match your search.</p>
      <button v-if="query" class="btn" @click="query = ''">Clear search</button>
    </div>

    <!-- ready -->
    <template v-else>
      <div class="grid">
        <ProductCard v-for="p in products" :key="p.id" :product="p" />
      </div>
      <nav v-if="lastPage > 1" class="pager" aria-label="Pagination">
        <button class="btn" :disabled="page <= 1" @click="page--">Previous</button>
        <span>Page {{ page }} of {{ lastPage }}</span>
        <button class="btn" :disabled="page >= lastPage" @click="page++">Next</button>
      </nav>
    </template>
  </main>
</template>

<style scoped>
.catalog { max-width: var(--container-max); margin: 0 auto; padding: var(--space-8) var(--container-pad); }
.catalog__head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-4); margin-bottom: var(--space-8); }
.catalog__head h1 { font-size: var(--text-2xl); margin: 0; }
.catalog__search input {
  font: inherit; padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border); border-radius: var(--radius-md); min-width: 16rem;
}
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--space-6); }
.skeleton { aspect-ratio: 4 / 5; background: var(--color-surface); border-radius: var(--radius-md); animation: pulse 1.2s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
.state { text-align: center; padding: var(--space-16) 0; color: var(--color-text-muted); }
.pager { display: flex; align-items: center; justify-content: center; gap: var(--space-4); margin-top: var(--space-12); }
.btn {
  font: inherit; min-height: 44px; padding: var(--space-2) var(--space-4);
  background: var(--color-accent); color: var(--color-accent-text);
  border: none; border-radius: var(--radius-md); cursor: pointer;
}
.btn:hover { background: var(--color-accent-hover); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
