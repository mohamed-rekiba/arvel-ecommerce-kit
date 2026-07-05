<script setup lang="ts">
// Only one coupon reaches the storefront's orange bar — the newest live one with announce=true wins.
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { onMounted, reactive, ref } from 'vue'
import { ApiError, api } from '../api'
import type { AdminCouponOut } from '../../api/gen/models'
import { t } from '../locale'

const coupons = ref<AdminCouponOut[]>([])
const loading = ref(true)
const notice = ref<string | null>(null)
const dialogOpen = ref(false)
const saving = ref(false)

const form = reactive({
  code: '',
  type: 'percent' as 'percent' | 'fixed',
  value: 10,
  announce: false
})
const typeOptions = [
  { label: '%', value: 'percent' },
  { label: '$', value: 'fixed' }
]

async function load() {
  loading.value = true
  notice.value = null
  try {
    coupons.value = await api.adminCoupons()
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('common.no_catalog') : t('common.load_error')
  } finally {
    loading.value = false
  }
}

async function create() {
  saving.value = true
  notice.value = null
  try {
    await api.createCoupon({
      code: form.code,
      type: form.type,
      value: form.type === 'fixed' ? Math.round(form.value * 100) : form.value,
      announce: form.announce
    })
    dialogOpen.value = false
    Object.assign(form, {
      code: '',
      type: 'percent',
      value: 10,
      announce: false
    })
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

async function patch(coupon: AdminCouponOut, body: { active?: boolean; announce?: boolean }) {
  try {
    const updated = await api.updateCoupon(coupon.id, body)
    coupons.value = coupons.value.map((c) => (c.id === updated.id ? updated : c))
  } catch {
    notice.value = t('common.save_error')
  }
}

onMounted(load)
</script>

<template>
  <section class="page">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('nav.catalog') }}</p>
        <h1>{{ t('nav.coupons') }}</h1>
        <p class="sub">{{ t('coupons.sub') }}</p>
      </div>
      <Button :label="t('coupons.new')" icon="pi pi-plus" @click="dialogOpen = true" />
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="coupons" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty
          ><p class="empty">{{ t('coupons.none') }}</p></template
        >
        <Column :header="t('coupons.code')">
          <template #body="{ data }"
            ><code class="code">{{ data.code }}</code></template
          >
        </Column>
        <Column :header="t('coupons.value')" style="width: 7rem">
          <template #body="{ data }">
            <Tag
              :value="
                data.type === 'percent' ? `−${data.value}%` : `−$${(data.value / 100).toFixed(2)}`
              "
              severity="warn"
            />
          </template>
        </Column>
        <Column :header="t('coupons.uses')" style="width: 6rem">
          <template #body="{ data }"
            >{{ data.uses }}{{ data.usage_limit ? ` / ${data.usage_limit}` : '' }}</template
          >
        </Column>
        <Column :header="t('coupons.active')" style="width: 6rem">
          <template #body="{ data }">
            <ToggleSwitch
              :modelValue="data.active"
              :aria-label="t('coupons.active')"
              @update:modelValue="patch(data, { active: !data.active })"
            />
          </template>
        </Column>
        <Column :header="t('coupons.announce')" style="width: 8rem">
          <template #body="{ data }">
            <ToggleSwitch
              :modelValue="data.announce"
              :aria-label="t('coupons.announce')"
              @update:modelValue="patch(data, { announce: !data.announce })"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <Dialog
      v-model:visible="dialogOpen"
      modal
      :header="t('coupons.new')"
      :style="{ width: '24rem' }"
    >
      <form class="form" @submit.prevent="create">
        <label class="field"
          ><span>{{ t('coupons.code') }}</span
          ><InputText v-model.trim="form.code" required
        /></label>
        <div class="row">
          <label class="field"
            ><span>{{ t('coupons.type') }}</span>
            <Select
              v-model="form.type"
              :options="typeOptions"
              optionLabel="label"
              optionValue="value"
            />
          </label>
          <label class="field"
            ><span>{{ t('coupons.value') }}</span>
            <InputNumber
              v-model="form.value"
              :min="1"
              :max="form.type === 'percent' ? 100 : 100000"
            />
          </label>
        </div>
        <label class="field field--switch"
          ><span>{{ t('coupons.announce') }}</span
          ><ToggleSwitch v-model="form.announce"
        /></label>
        <Button
          type="submit"
          :label="saving ? t('common.saving') : t('common.save')"
          :disabled="saving || !form.code"
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
.code {
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 700;
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
.field--switch {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.field--switch span {
  margin: 0;
}
.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}
</style>
