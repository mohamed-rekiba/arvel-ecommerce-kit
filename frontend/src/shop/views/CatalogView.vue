<script setup lang="ts">
import Select from 'primevue/select'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { type Category, type Product, api } from '../api'
import { cacheList, cacheProducts, getCachedList } from '../product-cache'
import ProductCard from '../components/ProductCard.vue'
import { t } from '../locale'

const route = useRoute()
const router = useRouter()

const products = ref<Product[]>([])
const categories = ref<Category[]>([])
const total = ref(0)
const lastPage = ref(1)
const status = ref<'loading' | 'error' | 'ready'>('loading')

const sortOptions = [
  { label: t('sort.featured'), value: 'featured' },
  { label: t('sort.price_asc'), value: 'price_asc' },
  { label: t('sort.price_desc'), value: 'price_desc' },
  { label: t('sort.newest'), value: 'newest' },
  { label: t('sort.name'), value: 'name' }
]

// filters are the URL — shareable, and the header search drives ?q here
const activeCategory = computed(() => (route.query.category as string) || '')
const q = computed(() => (route.query.q as string) || '')
const sort = computed(() => (route.query.sort as string) || 'featured')
const page = computed(() => Number(route.query.page) || 1)
const minPrice = computed(() => (route.query.min ? Number(route.query.min) : undefined))
const maxPrice = computed(() => (route.query.max ? Number(route.query.max) : undefined))
const priceMinInput = ref(route.query.min ? String(Number(route.query.min) / 100) : '')
const priceMaxInput = ref(route.query.max ? String(Number(route.query.max) / 100) : '')
function applyPrice() {
  setQuery({
    min: priceMinInput.value ? Math.round(Number(priceMinInput.value) * 100) : undefined,
    max: priceMaxInput.value ? Math.round(Number(priceMaxInput.value) * 100) : undefined,
    page: undefined
  })
}
const activeName = computed(
  () =>
    categories.value.find((c) => c.slug === activeCategory.value)?.translation.name ??
    t('catalog.all')
)

// Keyed by the exact query, so a back-nav repaints the same card set synchronously instead of
// refetching a frame too late for the morph.
const listKey = () =>
  `catalog:${JSON.stringify({ q: q.value, category: activeCategory.value, sort: sort.value, page: page.value, min: minPrice.value, max: maxPrice.value })}`
const seeded = getCachedList(listKey())
if (seeded) {
  products.value = seeded
  status.value = 'ready'
}

function setQuery(patch: Record<string, string | number | undefined>) {
  const query = { ...route.query, ...patch }
  for (const k of Object.keys(query)) if (!query[k]) delete query[k]
  router.replace({ name: 'catalog', query })
}

async function load() {
  if (!products.value.length) status.value = 'loading' // keep seeded cards on screen while refreshing
  try {
    const res = await api.products({
      q: q.value || undefined,
      category: activeCategory.value || undefined,
      sort: sort.value,
      page: page.value,
      minPrice: minPrice.value,
      maxPrice: maxPrice.value
    })
    products.value = res.data
    cacheProducts(res.data) // forward morph: PDP renders the image instantly
    cacheList(listKey(), res.data) // back morph: catalog repaints these cards synchronously on remount
    total.value = res.total
    lastPage.value = res.last_page
    status.value = 'ready'
  } catch {
    if (!products.value.length) status.value = 'error'
  }
}

onMounted(async () => {
  categories.value = await api.categories().catch(() => [])
  await load()
})
watch(() => route.query, load)
</script>

<template>
  <div class="shop-page">
    <aside class="filters">
      <div class="filters__group">
        <h3 class="filters__h">{{ t('catalog.categories') }}</h3>
        <ul class="cats">
          <li>
            <button
              class="cat"
              :class="{ on: !activeCategory }"
              @click="setQuery({ category: undefined, page: undefined })"
            >
              {{ t('catalog.all') }}
            </button>
          </li>
          <li v-for="c in categories" :key="c.id">
            <button
              class="cat"
              :class="{ on: c.slug === activeCategory }"
              @click="setQuery({ category: c.slug, page: undefined })"
            >
              {{ c.translation.name }}
            </button>
          </li>
        </ul>
      </div>
      <div class="filters__group">
        <h3 class="filters__h">{{ t('catalog.price') }}</h3>
        <form class="pricef" @submit.prevent="applyPrice">
          <input
            v-model.trim="priceMinInput"
            class="pricef__in"
            type="number"
            min="0"
            inputmode="decimal"
            :placeholder="t('catalog.min')"
            :aria-label="t('catalog.min')"
          />
          <span aria-hidden="true">–</span>
          <input
            v-model.trim="priceMaxInput"
            class="pricef__in"
            type="number"
            min="0"
            inputmode="decimal"
            :placeholder="t('catalog.max')"
            :aria-label="t('catalog.max')"
          />
          <button type="submit" class="pricef__go">
            {{ t('catalog.apply') }}
          </button>
        </form>
        <button
          v-if="minPrice != null || maxPrice != null"
          class="pricef__clear"
          @click="((priceMinInput = ''), (priceMaxInput = ''), applyPrice())"
        >
          {{ t('catalog.clear_filters') }}
        </button>
      </div>
    </aside>

    <main class="results">
      <div class="results__head">
        <div>
          <p class="eyebrow">{{ t('catalog.eyebrow') }}</p>
          <h1>{{ activeName }}</h1>
          <p class="count">
            <span v-if="status === 'ready'"
              >{{ total }} {{ total === 1 ? t('catalog.one') : t('catalog.many') }}</span
            >
            <span v-else>&nbsp;</span>
          </p>
        </div>
        <Select
          class="sort"
          :model-value="sort"
          :options="sortOptions"
          option-label="label"
          option-value="value"
          @update:model-value="(v: string) => setQuery({ sort: v, page: undefined })"
        />
      </div>

      <div v-if="status === 'loading'" class="grid">
        <div v-for="n in 9" :key="n" class="sk" />
      </div>
      <div v-else-if="status === 'error'" class="state">
        <p>{{ t('catalog.load_error') }}</p>
        <button class="link" @click="load">{{ t('common.retry') }}</button>
      </div>
      <div v-else-if="!products.length" class="state">
        <p v-if="q">{{ t('catalog.no_match', { q }) }}</p>
        <p v-else>{{ t('catalog.empty_category') }}</p>
        <button class="link" @click="setQuery({ q: undefined, category: undefined })">
          {{ t('catalog.clear_filters') }}
        </button>
      </div>
      <template v-else>
        <div class="grid">
          <ProductCard v-for="p in products" :key="p.id" :product="p" />
        </div>
        <nav v-if="lastPage > 1" class="pager" :aria-label="t('a11y.pagination')">
          <button class="link" :disabled="page <= 1" @click="setQuery({ page: page - 1 })">
            {{ t('common.back') }} {{ t('catalog.prev') }}
          </button>
          <span class="pager__n">{{ t('catalog.page_of', { page, last: lastPage }) }}</span>
          <button class="link" :disabled="page >= lastPage" @click="setQuery({ page: page + 1 })">
            {{ t('catalog.next') }} {{ t('common.fwd') }}
          </button>
        </nav>
      </template>
    </main>
  </div>
</template>

<style scoped>
.shop-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: clamp(1.5rem, 4vw, 3rem) clamp(1.25rem, 5vw, 3.5rem) 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: clamp(2rem, 4vw, 3.5rem);
}
.eyebrow {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: var(--accent);
  font-weight: 600;
}
.filters {
  position: static;
}
.filters__h {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--text-subtle);
  font-weight: 600;
  margin: 0 0 14px;
}
.cats {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 2px;
}
.cat {
  display: block;
  width: 100%;
  text-align: start;
  border: 0;
  background: none;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  font: inherit;
  font-size: 14px;
  color: var(--text-muted);
  cursor: pointer;
  transition:
    background var(--motion-base),
    color var(--motion-base);
}
.cat:hover {
  background: color-mix(in srgb, var(--text) 5%, transparent);
  color: var(--text);
}
.cat.on {
  background: color-mix(in srgb, var(--accent) 14%, transparent);
  color: var(--accent);
  font-weight: 600;
}

.results__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: clamp(1.5rem, 3vw, 2.25rem);
}
.results__head h1 {
  font-family: var(--font-display);
  font-size: clamp(1.6rem, 3vw, 2.4rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 8px 0 4px;
}
.count {
  color: var(--text-subtle);
  font-size: 13px;
  margin: 0;
}
.sort {
  min-width: 200px;
}

.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: clamp(1.25rem, 2.5vw, 2.25rem);
}
.sk {
  aspect-ratio: 4/5;
  border-radius: var(--radius-lg);
  background: var(--surface-2);
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  50% {
    opacity: 0.55;
  }
}
.state {
  text-align: center;
  padding: 80px 0;
  color: var(--text-subtle);
}
.link {
  border: 0;
  background: none;
  color: var(--accent);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  margin-top: 12px;
}
.link:disabled {
  opacity: 0.4;
  cursor: default;
}
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-top: 48px;
}
.pager__n {
  color: var(--text-subtle);
  font-size: 13px;
}

@media (min-width: 640px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (min-width: 1024px) {
  .shop-page {
    grid-template-columns: 220px 1fr;
  }
  .filters {
    position: sticky;
    top: 96px;
    align-self: start;
  }
  .cats {
    flex-direction: column;
  }
  .grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
.pricef {
  display: flex;
  align-items: center;
  gap: 6px;
}
.pricef__in {
  width: 74px;
  padding: 7px 9px;
  font-size: 13px;
}
.pricef__go {
  border: 1px solid var(--accent);
  background: none;
  color: var(--accent-text);
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.pricef__go:hover {
  background: var(--accent);
  color: var(--on-accent);
}
.pricef__clear {
  margin-top: 8px;
  border: 0;
  background: none;
  color: var(--text-subtle);
  font: inherit;
  font-size: 12px;
  text-decoration: underline;
  cursor: pointer;
}
</style>
