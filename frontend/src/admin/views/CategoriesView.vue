<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError, api } from '../api'
import type { AdminCategory } from '../api'
import { t } from '../locale'

const router = useRouter()
const categories = ref<AdminCategory[]>([])
const loading = ref(true)
const notice = ref<string | null>(null)
const q = ref('')

const filtered = computed(() => {
  const term = q.value.trim().toLowerCase()
  if (!term) return categories.value
  return categories.value.filter(
    (c) =>
      c.translations.some((tr) => (tr.name ?? '').toLowerCase().includes(term)) ||
      c.slug.toLowerCase().includes(term)
  )
})

function catName(category: AdminCategory): string {
  return category.translations.find((t) => t.locale === 'en')?.name ?? category.slug
}

function localeName(category: AdminCategory, locale: string): string | null {
  return category.translations.find((tr) => tr.locale === locale)?.name ?? null
}

async function load() {
  loading.value = true
  try {
    categories.value = (await api.adminCategories()).data
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('common.no_catalog') : t('common.load_error')
  } finally {
    loading.value = false
  }
}

async function remove(category: AdminCategory) {
  if (!window.confirm(t('categories.delete_confirm', { name: catName(category) }))) return
  notice.value = null
  try {
    await api.deleteCategory(category.id)
    await load()
  } catch (e) {
    notice.value =
      e instanceof ApiError
        ? (Object.values(e.errors)[0]?.[0] ?? t('common.delete_error'))
        : t('common.delete_error')
  }
}

onMounted(load)
</script>

<template>
  <section class="apage">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('nav.catalog') }}</p>
        <h1>{{ t('nav.categories') }}</h1>
        <p class="sub">{{ t('categories.sub') }}</p>
      </div>
    </header>

    <div class="toolbar">
      <span class="search">
        <i class="pi pi-search" />
        <InputText v-model="q" :placeholder="t('categories.search_ph')" />
      </span>
      <Button
        class="add"
        :label="t('categories.new')"
        icon="pi pi-plus"
        @click="router.push('/admin/categories/new')"
      />
    </div>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="filtered" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty>
          <p class="empty">{{ t('categories.none') }}</p>
        </template>
        <Column :header="t('categories.category')">
          <template #body="{ data }">
            <div class="prod">
              <div class="thumb"><i class="pi pi-folder" /></div>
              <div>
                <div class="pname">{{ catName(data) }}</div>
                <div class="pslug">
                  /{{ data.slug }}
                  <span v-if="localeName(data, 'fr')">· fr {{ localeName(data, 'fr') }}</span>
                  <span v-if="localeName(data, 'ar')">· ar {{ localeName(data, 'ar') }}</span>
                </div>
              </div>
            </div>
          </template>
        </Column>
        <Column :header="t('categories.parent')">
          <template #body="{ data }">
            <span class="muted">{{
              data.parent_id
                ? catName(categories.find((c) => c.id === data.parent_id) ?? data)
                : '—'
            }}</span>
          </template>
        </Column>
        <Column :header="t('categories.published')">
          <template #body="{ data }">
            <Tag
              :value="data.published ? t('categories.published') : t('products.hidden')"
              :severity="data.published ? 'success' : 'secondary'"
            />
          </template>
        </Column>
        <Column :header="t('products.storefront')">
          <template #body="{ data }">
            <Tag
              :value="data.is_visible ? t('products.visible') : t('products.hidden')"
              :severity="data.is_visible ? 'success' : 'secondary'"
            />
          </template>
        </Column>
        <Column header="" header-style="width: 8rem">
          <template #body="{ data }">
            <Button
              icon="pi pi-pencil"
              text
              rounded
              :aria-label="t('common.edit')"
              @click="router.push(`/admin/categories/${data.id}`)"
            />
            <Button
              icon="pi pi-trash"
              text
              rounded
              severity="danger"
              :aria-label="t('common.delete')"
              @click="remove(data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>
  </section>
</template>
