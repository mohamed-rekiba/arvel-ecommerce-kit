<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { type AdminBanner, ApiError, api } from '../api'
import { t } from '../locale'

const router = useRouter()
const banners = ref<AdminBanner[]>([])
const loading = ref(true)
const notice = ref<string | null>(null)
const q = ref('')

const filtered = computed(() => {
  const term = q.value.trim().toLowerCase()
  if (!term) return banners.value
  return banners.value.filter(
    (b) =>
      (b.translations.en?.title ?? '').toLowerCase().includes(term) ||
      b.cta_to.toLowerCase().includes(term)
  )
})

async function load() {
  loading.value = true
  notice.value = null
  try {
    banners.value = await api.adminBanners()
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('common.no_catalog') : t('common.load_error')
  } finally {
    loading.value = false
  }
}

async function toggleActive(banner: AdminBanner) {
  try {
    const updated = await api.updateBanner(banner.id, { active: !banner.active })
    banners.value = banners.value.map((b) => (b.id === updated.id ? updated : b))
  } catch {
    notice.value = t('common.save_error')
  }
}

async function remove(banner: AdminBanner) {
  if (
    !window.confirm(
      t('banners.delete_confirm', {
        title: banner.translations.en?.title ?? '#' + banner.id
      })
    )
  )
    return
  try {
    await api.deleteBanner(banner.id)
    await load()
  } catch {
    notice.value = t('common.delete_error')
  }
}

onMounted(load)
</script>

<template>
  <section class="apage">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('reviews.eyebrow') }}</p>
        <h1>{{ t('nav.banners') }}</h1>
        <p class="sub">{{ t('banners.sub') }}</p>
      </div>
    </header>

    <div class="toolbar">
      <span class="search">
        <i class="pi pi-search" />
        <InputText v-model="q" :placeholder="t('banners.search_ph')" />
      </span>
      <Button
        class="add"
        :label="t('banners.new')"
        icon="pi pi-plus"
        @click="router.push('/admin/banners/new')"
      />
    </div>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="filtered" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty>
          <p class="empty">{{ t('banners.none') }}</p>
        </template>
        <Column :header="t('banners.image')" header-style="width: 9rem">
          <template #body="{ data }">
            <img v-if="data.image_url" class="bthumb" :src="data.image_url" alt="" />
            <span v-else class="muted">—</span>
          </template>
        </Column>
        <Column :header="t('banners.slide')">
          <template #body="{ data }">
            <div class="pname">{{ data.translations.en?.title ?? '—' }}</div>
            <div class="muted">
              {{ data.cta_to }} · {{ Object.keys(data.translations).join(', ') }}
            </div>
          </template>
        </Column>
        <Column :header="t('banners.sort')" header-style="width: 5rem">
          <template #body="{ data }"><span class="muted">{{ data.sort }}</span></template>
        </Column>
        <Column :header="t('common.status')" header-style="width: 7rem">
          <template #body="{ data }">
            <Tag
              :value="data.active ? t('banners.live') : t('deals.paused')"
              :severity="data.active ? 'success' : 'secondary'"
            />
          </template>
        </Column>
        <Column header="" header-style="width: 13rem">
          <template #body="{ data }">
            <Button
              icon="pi pi-pencil"
              text
              rounded
              :aria-label="t('common.edit')"
              @click="router.push(`/admin/banners/${data.id}`)"
            />
            <Button
              size="small"
              outlined
              severity="secondary"
              :label="data.active ? t('deals.pause') : t('deals.resume')"
              @click="toggleActive(data)"
            />
            <Button
              size="small"
              text
              severity="danger"
              :label="t('common.delete')"
              @click="remove(data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>
  </section>
</template>

<style scoped>
.bthumb {
  width: 110px;
  aspect-ratio: 16 / 7;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}
</style>
