<script setup lang="ts">
// The storefront charges the deal price for real once live, so the LIVE column isn't just cosmetic.
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { computed, onMounted, reactive, ref } from 'vue'
import { type AdminDeal, type AdminProduct, ApiError, api, name } from '../api'
import { currentLocale } from '../../lib/i18n'
import { t } from '../locale'

const deals = ref<AdminDeal[]>([])
const products = ref<AdminProduct[]>([])
const loading = ref(true)
const notice = ref<string | null>(null)
const dialogOpen = ref(false)
const saving = ref(false)

const form = reactive({
  product_id: null as number | null,
  percent_off: 10,
  hours: 24
})
const productOptions = computed(() => products.value.map((p) => ({ id: p.id, label: name(p) })))

async function load() {
  loading.value = true
  notice.value = null
  try {
    deals.value = await api.adminDeals()
    if (!products.value.length) products.value = (await api.products()).data
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('common.no_catalog') : t('common.load_error')
  } finally {
    loading.value = false
  }
}

async function create() {
  if (form.product_id == null) return
  saving.value = true
  notice.value = null
  try {
    const now = new Date()
    const ends = new Date(now.getTime() + form.hours * 3600 * 1000)
    await api.createDeal({
      product_id: form.product_id,
      percent_off: form.percent_off,
      starts_at: now.toISOString(),
      ends_at: ends.toISOString(),
      active: true
    })
    dialogOpen.value = false
    Object.assign(form, { product_id: null, percent_off: 10, hours: 24 })
    await load()
  } catch (e) {
    notice.value =
      e instanceof ApiError
        ? (Object.values(e.errors)[0]?.[0] ?? t('common.save_error'))
        : t('common.save_error')
  } finally {
    saving.value = false
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
  <section class="page">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('nav.catalog') }}</p>
        <h1>{{ t('nav.deals') }}</h1>
        <p class="sub">{{ t('deals.sub') }}</p>
      </div>
      <Button :label="t('deals.new')" icon="pi pi-plus" @click="dialogOpen = true" />
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="deals" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty
          ><p class="empty">{{ t('deals.none') }}</p></template
        >
        <Column :header="t('products.product')">
          <template #body="{ data }"
            ><span class="pname">{{ data.product_name }}</span></template
          >
        </Column>
        <Column :header="t('deals.percent')">
          <template #body="{ data }"
            ><Tag :value="`−${data.percent_off}%`" severity="warn"
          /></template>
        </Column>
        <Column :header="t('deals.window')">
          <template #body="{ data }">
            <span class="muted">{{ when(data.starts_at) }} → {{ when(data.ends_at) }}</span>
          </template>
        </Column>
        <Column :header="t('common.status')" style="width: 8rem">
          <template #body="{ data }">
            <Tag
              :value="
                data.live ? t('deals.live') : data.active ? t('deals.scheduled') : t('deals.paused')
              "
              :severity="data.live ? 'success' : data.active ? 'info' : 'secondary'"
            />
          </template>
        </Column>
        <Column header="" style="width: 12rem">
          <template #body="{ data }">
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

    <Dialog v-model:visible="dialogOpen" modal :header="t('deals.new')" :style="{ width: '26rem' }">
      <form class="form" @submit.prevent="create">
        <label class="field"
          ><span>{{ t('products.product') }}</span>
          <Select
            v-model="form.product_id"
            :options="productOptions"
            optionLabel="label"
            optionValue="id"
            filter
          />
        </label>
        <label class="field"
          ><span>{{ t('deals.percent') }}</span>
          <InputNumber v-model="form.percent_off" :min="1" :max="90" suffix="%" />
        </label>
        <label class="field"
          ><span>{{ t('deals.duration') }}</span>
          <InputNumber v-model="form.hours" :min="1" :max="720" :suffix="` ${t('deal.hrs')}`" />
        </label>
        <Button
          type="submit"
          :label="saving ? t('common.saving') : t('common.save')"
          :disabled="saving || form.product_id == null"
        />
      </form>
    </Dialog>
  </section>
</template>

<style scoped>
.eyebrow {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--accent-text);
  font-weight: 600;
}
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.head h1 {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  margin: 6px 0 2px;
}
.sub {
  color: var(--text-muted);
  font-size: 13px;
  margin: 0;
}
.notice {
  background: var(--danger-bg);
  color: var(--danger-fg);
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 13px;
  margin-bottom: 16px;
}
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-1);
  overflow: hidden;
}
.pname {
  font-weight: 600;
  font-size: 13.5px;
}
.muted {
  color: var(--text-muted);
  font-size: 12.5px;
}
.empty {
  text-align: center;
  color: var(--text-subtle);
  padding: 24px 0;
}
.form .field {
  display: block;
  margin-bottom: var(--space-4);
}
.field span {
  display: block;
  font-size: var(--text-sm);
  margin-bottom: var(--space-1);
}
.field :deep(input),
.field :deep(.p-select) {
  width: 100%;
}
</style>
