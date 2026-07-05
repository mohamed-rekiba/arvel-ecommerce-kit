<script setup lang="ts">
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError, api } from '../api'
import type { AdminCouponOut } from '../../api/gen/models'
import { t } from '../locale'
import EditorPage from '../components/EditorPage.vue'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.params.id === 'new')
const id = computed(() => (isNew.value ? null : Number(route.params.id)))

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)

// value/minSubtotal are held in MAJOR units when the type is fixed ($), plain % when percent.
const form = reactive({
  code: '',
  type: 'percent' as 'percent' | 'fixed',
  value: 10,
  minSubtotal: 0,
  usage_limit: null as number | null,
  per_customer_limit: null as number | null,
  active: true,
  announce: false
})
const typeOptions = [
  { label: t('coupons.percent_off'), value: 'percent' },
  { label: t('coupons.fixed_off'), value: 'fixed' }
]

async function load() {
  loading.value = true
  try {
    if (id.value !== null) {
      const c = (await api.adminCoupons()).find((x) => x.id === id.value)
      if (c) hydrate(c)
    }
  } catch {
    error.value = t('common.load_error')
  } finally {
    loading.value = false
  }
}

function hydrate(c: AdminCouponOut) {
  form.code = c.code
  form.type = c.type
  form.value = c.type === 'fixed' ? c.value / 100 : c.value
  form.minSubtotal = c.min_subtotal_cents / 100
  form.usage_limit = c.usage_limit
  form.per_customer_limit = c.per_customer_limit
  form.active = c.active
  form.announce = c.announce
}

async function save() {
  saving.value = true
  error.value = null
  const minCents = Math.round(form.minSubtotal * 100)
  try {
    if (id.value === null) {
      await api.createCoupon({
        code: form.code,
        type: form.type,
        value: form.type === 'fixed' ? Math.round(form.value * 100) : form.value,
        min_subtotal_cents: minCents,
        usage_limit: form.usage_limit,
        per_customer_limit: form.per_customer_limit,
        announce: form.announce
      })
    } else {
      await api.updateCoupon(id.value, {
        min_subtotal_cents: minCents,
        usage_limit: form.usage_limit,
        per_customer_limit: form.per_customer_limit,
        active: form.active,
        announce: form.announce
      })
    }
    router.push('/admin/coupons')
  } catch (e) {
    error.value =
      e instanceof ApiError
        ? (Object.values(e.errors)[0]?.[0] ?? t('common.save_error'))
        : t('common.save_error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <EditorPage
    :title="isNew ? t('coupons.new') : form.code"
    back-to="/admin/coupons"
    :back-label="t('nav.coupons')"
    :save-label="saving ? t('common.saving') : t('common.save')"
    :saving="saving"
    :disabled="saving || !form.code.trim()"
    @save="save"
  >
    <div class="ecard">
      <h2>{{ t('coupons.terms') }}</h2>
      <p v-if="error" class="notice" role="alert">{{ error }}</p>
      <p v-if="!isNew" class="ehint">{{ t('coupons.locked_hint') }}</p>
      <div class="form">
        <label class="fld">
          <span>{{ t('coupons.code') }}</span>
          <InputText v-model.trim="form.code" :disabled="!isNew" />
        </label>
        <div class="frow">
          <label class="fld">
            <span>{{ t('coupons.type') }}</span>
            <Select
              v-model="form.type"
              :options="typeOptions"
              option-label="label"
              option-value="value"
              :disabled="!isNew"
            />
          </label>
          <label class="fld">
            <span>{{ form.type === 'percent' ? t('coupons.percent_val') : t('coupons.amount') }}</span>
            <InputNumber
              v-if="form.type === 'percent'"
              v-model="form.value"
              :min="1"
              :max="100"
              suffix="%"
              :disabled="!isNew"
            />
            <InputNumber
              v-else
              v-model="form.value"
              mode="currency"
              currency="USD"
              :min="0"
              :disabled="!isNew"
            />
          </label>
        </div>
      </div>
    </div>

    <div class="ecard">
      <h2>{{ t('coupons.rules') }}</h2>
      <div class="form">
        <div class="frow">
          <label class="fld">
            <span>{{ t('coupons.min_subtotal') }}</span>
            <InputNumber v-model="form.minSubtotal" mode="currency" currency="USD" :min="0" />
          </label>
          <label class="fld">
            <span>{{ t('coupons.usage_limit') }}</span>
            <InputNumber
              v-model="form.usage_limit"
              :min="0"
              :placeholder="t('coupons.unlimited')"
            />
          </label>
        </div>
        <label class="fld">
          <span>{{ t('coupons.per_customer') }}</span>
          <InputNumber
            v-model="form.per_customer_limit"
            :min="0"
            :placeholder="t('coupons.unlimited')"
          />
        </label>
        <label v-if="!isNew" class="fld fld--row">
          <span>{{ t('coupons.active') }}</span>
          <ToggleSwitch v-model="form.active" />
        </label>
        <label class="fld fld--row">
          <span>{{ t('coupons.announce') }}</span>
          <ToggleSwitch v-model="form.announce" />
        </label>
      </div>
    </div>
  </EditorPage>
</template>
