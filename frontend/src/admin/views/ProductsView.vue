<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { type AdminProduct, ApiError, api, formatPrice, name } from '../api'
import { t } from '../locale'

const router = useRouter()

// ── list state ──
const products = ref<AdminProduct[]>([])
const total = ref(0)
const lastPage = ref(1)
const page = ref(1)
const status = ref<'loading' | 'error' | 'ready'>('loading')
const notice = ref<string | null>(null)
const view = ref<'list' | 'grid'>('list')
const filtersOpen = ref(true)
const selected = ref<AdminProduct[]>([])

// ── filters ──
const q = ref('')
const categoryId = ref<number | null>(null)
const vendorId = ref<number | null>(null)
const priceIdx = ref(0)
const statusVal = ref<'all' | 'active' | 'inactive'>('all')
const sort = ref('newest')
const archived = ref(false)

const PRICES = [
  {
    label: t('products.price_any'),
    min: undefined as number | undefined,
    max: undefined as number | undefined
  },
  { label: '< $50', min: 0, max: 4999 },
  { label: '$50 – $100', min: 5000, max: 10000 },
  { label: '$100 – $200', min: 10001, max: 20000 },
  { label: '> $200', min: 20001, max: undefined }
]
const SORTS = [
  { label: t('products.sort_newest'), value: 'newest' },
  { label: t('products.sort_oldest'), value: 'oldest' },
  { label: t('products.sort_price_asc'), value: 'price_asc' },
  { label: t('products.sort_price_desc'), value: 'price_desc' }
]
const SHOWS = [
  { label: t('products.all_products'), value: 'active_view' },
  { label: t('products.archived'), value: 'archived' }
]
const STATUSES = [
  { label: t('products.all_status'), value: 'all' },
  { label: t('products.active_only'), value: 'active' },
  { label: t('products.inactive_only'), value: 'inactive' }
]

const categories = ref<{ label: string; value: number | null }[]>([
  { label: t('products.all_categories'), value: null }
])
const vendors = ref<{ label: string; value: number | null }[]>([
  { label: t('products.all_stores'), value: null }
])
const showVal = computed({
  get: () => (archived.value ? 'archived' : 'active_view'),
  set: (v: string) => (archived.value = v === 'archived')
})

async function load() {
  status.value = 'loading'
  selected.value = []
  try {
    const price = PRICES[priceIdx.value]
    const res = await api.products({
      page: page.value,
      archived: archived.value,
      q: q.value.trim() || undefined,
      category_id: categoryId.value ?? undefined,
      vendor_id: vendorId.value ?? undefined,
      price_min: price?.min,
      price_max: price?.max,
      active: statusVal.value === 'all' ? undefined : statusVal.value,
      sort: sort.value
    })
    products.value = res.data
    total.value = res.total
    lastPage.value = res.last_page
    status.value = 'ready'
  } catch (e) {
    status.value = 'error'
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('common.no_catalog') : t('products.load_error')
  }
}

// re-load on any filter change (debounced so typing in search doesn't spam the API)
let timer: ReturnType<typeof setTimeout> | undefined
watch([q, categoryId, vendorId, priceIdx, statusVal, sort, archived], () => {
  page.value = 1
  clearTimeout(timer)
  timer = setTimeout(load, 250)
})
watch(page, load)

onMounted(async () => {
  const cats = await api
    .adminCategories()
    .then((r) => r.data)
    .catch(() => [])
  const vends = await api.vendors().catch(() => [])
  categories.value = [
    { label: t('products.all_categories'), value: null },
    ...cats.map((c) => ({ label: catName(c), value: c.id }))
  ]
  vendors.value = [
    { label: t('products.all_stores'), value: null },
    ...vends.map((v) => ({ label: v.name, value: v.id }))
  ]
  await load()
})

function catName(c: { translations?: { locale?: string; name?: string }[] }): string {
  const tr = c.translations ?? []
  return tr.find((x) => x.locale === 'en')?.name ?? tr[0]?.name ?? '—'
}

// ── stock bar ──
const STOCK_CAP = 1000
function stockTone(s: number): 'green' | 'amber' | 'red' {
  return s >= 200 ? 'green' : s >= 80 ? 'amber' : 'red'
}
function stockPct(s: number): number {
  return Math.min(100, Math.round((s / STOCK_CAP) * 100))
}

// ── inline active toggle ──
async function toggleActive(p: AdminProduct, val: boolean) {
  const prev = p.published
  p.published = val
  try {
    await api.updateProduct(p.id, { published: val })
  } catch {
    p.published = prev
    notice.value = t('products.save_error')
  }
}

// ── row + bulk delete ──
async function removeOne(p: AdminProduct) {
  if (!window.confirm(t('products.archive_confirm', { name: name(p) }))) return
  notice.value = null
  try {
    await api.deleteProduct(p.id)
    await load()
  } catch {
    notice.value = t('products.archive_error')
  }
}
async function restore(p: AdminProduct) {
  try {
    await api.restoreProduct(p.id)
    await load()
  } catch {
    notice.value = t('products.restore_error')
  }
}
async function archiveSelected() {
  if (!selected.value.length) return
  if (!window.confirm(t('products.archive_n', { n: selected.value.length }))) return
  for (const p of selected.value) await api.deleteProduct(p.id).catch(() => {})
  await load()
}

// ── create / edit ── the full editor (translations · variants · gallery) lives at
// /admin/products/:id — route to it rather than a shallow drawer, so every product
// feature stays reachable from the list.
function openNew() {
  router.push('/admin/products/new')
}
function openEdit(p: AdminProduct) {
  router.push(`/admin/products/${p.id}`)
}
</script>

<template>
  <section class="apage">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('nav.catalog') }}</p>
        <h1>{{ t('nav.products') }}</h1>
        <p class="sub">{{ t('products.sub') }}</p>
      </div>
    </header>

    <!-- toolbar -->
    <div class="toolbar">
      <div class="viewtog" role="group" :aria-label="t('products.view')">
        <button
          :class="{ on: view === 'list' }"
          :aria-label="t('products.list_view')"
          @click="view = 'list'"
        >
          <i class="pi pi-bars" />
        </button>
        <button
          :class="{ on: view === 'grid' }"
          :aria-label="t('products.grid_view')"
          @click="view = 'grid'"
        >
          <i class="pi pi-th-large" />
        </button>
      </div>
      <span class="search">
        <i class="pi pi-search" />
        <InputText v-model="q" :placeholder="t('products.search_ph')" />
      </span>
      <Select
        v-model="showVal"
        :options="SHOWS"
        option-label="label"
        option-value="value"
        class="tsel"
      />
      <Select
        v-model="sort"
        :options="SORTS"
        option-label="label"
        option-value="value"
        class="tsel"
      />
      <Button
        :label="t('products.filter')"
        icon="pi pi-filter"
        severity="secondary"
        outlined
        @click="filtersOpen = !filtersOpen"
      />
      <Button class="add" :label="t('products.new')" icon="pi pi-plus" @click="openNew" />
    </div>

    <!-- filter row -->
    <div v-show="filtersOpen && !archived" class="filters">
      <label>
        <span>{{ t('products.f_category') }}</span>
        <Select
          v-model="categoryId"
          :options="categories"
          option-label="label"
          option-value="value"
          :placeholder="t('products.all_categories')"
        />
      </label>
      <label>
        <span>{{ t('products.f_price') }}</span>
        <Select
          v-model="priceIdx"
          :options="PRICES.map((p, i) => ({ label: p.label, value: i }))"
          option-label="label"
          option-value="value"
        />
      </label>
      <label>
        <span>{{ t('products.f_status') }}</span>
        <Select v-model="statusVal" :options="STATUSES" option-label="label" option-value="value" />
      </label>
      <label>
        <span>{{ t('products.f_store') }}</span>
        <Select
          v-model="vendorId"
          :options="vendors"
          option-label="label"
          option-value="value"
          :placeholder="t('products.all_stores')"
        />
      </label>
    </div>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <!-- bulk action bar -->
    <div v-if="selected.length" class="bulk">
      <span>{{ t('products.selected', { n: selected.length }) }}</span>
      <Button
        :label="t('products.archive_selected')"
        icon="pi pi-trash"
        severity="danger"
        text
        @click="archiveSelected"
      />
    </div>

    <!-- LIST view -->
    <div v-if="view === 'list'" class="panel">
      <DataTable
        v-model:selection="selected"
        :value="products"
        :loading="status === 'loading'"
        data-key="id"
        size="small"
        striped-rows
      >
        <template #empty
          ><p class="empty">{{ t('products.none') }}</p></template
        >
        <Column selection-mode="multiple" header-style="width:3rem" />
        <Column :header="t('products.product')">
          <template #body="{ data }">
            <div class="prod">
              <div class="thumb">
                <img v-if="data.image_url" :src="data.image_url" alt="" /><i
                  v-else
                  class="pi pi-image"
                />
              </div>
              <div>
                <div class="pname">{{ name(data) }}</div>
                <div class="pid">ID: {{ data.slug }}</div>
              </div>
            </div>
          </template>
        </Column>
        <Column :header="t('products.price')">
          <template #body="{ data }"
            ><span class="price">{{ formatPrice(data.price_cents ?? 0) }}</span></template
          >
        </Column>
        <Column :header="t('products.stock')">
          <template #body="{ data }">
            <div class="stock">
              <div class="stock__bar">
                <span
                  :class="`s-${stockTone(data.stock ?? 0)}`"
                  :style="{ width: `${stockPct(data.stock ?? 0)}%` }"
                />
              </div>
              <span class="stock__n"
                >{{ data.stock ?? 0 }}<small>/{{ STOCK_CAP }}</small></span
              >
            </div>
          </template>
        </Column>
        <Column :header="t('products.col_active')" header-style="width:6rem">
          <template #body="{ data }">
            <ToggleSwitch
              v-if="!archived"
              :model-value="!!data.published"
              @update:model-value="(v: boolean) => toggleActive(data, v)"
            />
            <Tag v-else :value="t('products.archived')" severity="secondary" />
          </template>
        </Column>
        <Column header="" header-style="width:7rem">
          <template #body="{ data }">
            <template v-if="archived">
              <Button :label="t('products.restore')" size="small" outlined @click="restore(data)" />
            </template>
            <template v-else>
              <Button
                icon="pi pi-pencil"
                text
                rounded
                :aria-label="t('common.edit')"
                @click="openEdit(data)"
              />
              <Button
                icon="pi pi-trash"
                text
                rounded
                severity="danger"
                :aria-label="t('products.archive')"
                @click="removeOne(data)"
              />
            </template>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- GRID view -->
    <div v-else class="grid">
      <article v-for="p in products" :key="p.id" class="card">
        <div class="card__img">
          <img v-if="p.image_url" :src="p.image_url" alt="" /><i v-else class="pi pi-image" />
        </div>
        <div class="card__body">
          <div class="pname">{{ name(p) }}</div>
          <div class="pid">ID: {{ p.slug }}</div>
          <div class="card__row">
            <span class="price">{{ formatPrice(p.price_cents ?? 0) }}</span>
            <ToggleSwitch
              v-if="!archived"
              :model-value="!!p.published"
              @update:model-value="(v: boolean) => toggleActive(p, v)"
            />
          </div>
          <div class="stock">
            <div class="stock__bar">
              <span
                :class="`s-${stockTone(p.stock ?? 0)}`"
                :style="{ width: `${stockPct(p.stock ?? 0)}%` }"
              />
            </div>
            <span class="stock__n">{{ p.stock ?? 0 }}</span>
          </div>
          <div class="card__act">
            <Button
              icon="pi pi-pencil"
              text
              rounded
              :aria-label="t('common.edit')"
              @click="openEdit(p)"
            />
            <Button
              icon="pi pi-trash"
              text
              rounded
              severity="danger"
              :aria-label="t('products.archive')"
              @click="removeOne(p)"
            />
          </div>
        </div>
      </article>
      <p v-if="status === 'ready' && !products.length" class="empty">{{ t('products.none') }}</p>
    </div>

    <nav v-if="lastPage > 1" class="pager">
      <Button icon="pi pi-chevron-left" text :disabled="page <= 1" @click="page--" />
      <span>{{ page }} / {{ lastPage }} · {{ total }}</span>
      <Button icon="pi pi-chevron-right" text :disabled="page >= lastPage" @click="page++" />
    </nav>
  </section>
</template>
