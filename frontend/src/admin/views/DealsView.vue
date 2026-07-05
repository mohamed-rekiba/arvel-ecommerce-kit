<script setup lang="ts">
// The storefront charges the deal price for real once live, so the LIVE column isn't just cosmetic.
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { type AdminDeal, ApiError, api } from '../api'
import { currentLocale } from '../../lib/i18n'
import { t } from '../locale'

const router = useRouter()
const deals = ref<AdminDeal[]>([])
const loading = ref(true)
const notice = ref<string | null>(null)
const q = ref('')

const filtered = computed(() => {
  const term = q.value.trim().toLowerCase()
  if (!term) return deals.value
  return deals.value.filter((d) => (d.product_name ?? '').toLowerCase().includes(term))
})

async function load() {
  loading.value = true
  notice.value = null
  try {
    deals.value = await api.adminDeals()
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('common.no_catalog') : t('common.load_error')
  } finally {
    loading.value = false
  }
}

async function toggleActive(deal: AdminDeal) {
  notice.value = null
  try {
    const updated = await api.updateDeal(deal.id, { active: !deal.active })
    deals.value = deals.value.map((d) => (d.id === updated.id ? updated : d))
  } catch {
    notice.value = t('common.save_error')
  }
}

async function remove(deal: AdminDeal) {
  if (!window.confirm(t('deals.delete_confirm', { name: deal.product_name }))) return
  try {
    await api.deleteDeal(deal.id)
    await load()
  } catch {
    notice.value = t('common.delete_error')
  }
}

const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString(currentLocale()) : '—')
onMounted(load)
</script>

<template>
  <section class="apage">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('nav.catalog') }}</p>
        <h1>{{ t('nav.deals') }}</h1>
        <p class="sub">{{ t('deals.sub') }}</p>
      </div>
    </header>

    <div class="toolbar">
      <span class="search">
        <i class="pi pi-search" />
        <InputText v-model="q" :placeholder="t('deals.search_ph')" />
      </span>
      <Button
        class="add"
        :label="t('deals.new')"
        icon="pi pi-plus"
        @click="router.push('/admin/deals/new')"
      />
    </div>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="filtered" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty>
          <p class="empty">{{ t('deals.none') }}</p>
        </template>
        <Column :header="t('products.product')">
          <template #body="{ data }">
            <span class="pname">{{ data.product_name }}</span>
          </template>
        </Column>
        <Column :header="t('deals.percent')">
          <template #body="{ data }">
            <Tag :value="`−${data.percent_off}%`" severity="warn" />
          </template>
        </Column>
        <Column :header="t('deals.window')">
          <template #body="{ data }">
            <span class="muted">{{ when(data.starts_at) }} → {{ when(data.ends_at) }}</span>
          </template>
        </Column>
        <Column :header="t('common.status')" header-style="width: 8rem">
          <template #body="{ data }">
            <Tag
              :value="
                data.live ? t('deals.live') : data.active ? t('deals.scheduled') : t('deals.paused')
              "
              :severity="data.live ? 'success' : data.active ? 'info' : 'secondary'"
            />
          </template>
        </Column>
        <Column header="" header-style="width: 12rem">
          <template #body="{ data }">
            <Button
              size="small"
              outlined
              severity="secondary"
              :label="data.active ? t('deals.pause') : t('deals.resume')"
              @click="toggleActive(data)"
            />
            <Button
              icon="pi pi-pencil"
              text
              rounded
              :aria-label="t('common.edit')"
              @click="router.push(`/admin/deals/${data.id}`)"
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
.pname {
  font-weight: 600;
  font-size: 13.5px;
}
</style>
