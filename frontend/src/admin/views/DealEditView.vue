<script setup lang="ts">
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { type AdminProduct, ApiError, api, name } from '../api'
import { currentLocale } from '../../lib/i18n'
import { t } from '../locale'
import EditorPage from '../components/EditorPage.vue'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.params.id === 'new')
const id = computed(() => (isNew.value ? null : Number(route.params.id)))

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const products = ref<AdminProduct[]>([])
const productName = ref('')
const window = reactive({ starts_at: null as string | null, ends_at: null as string | null })

const form = reactive({
  product_id: null as number | null,
  percent_off: 10,
  hours: 24,
  active: true
})
const productOptions = computed(() => products.value.map((p) => ({ id: p.id, label: name(p) })))
const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString(currentLocale()) : '—')

async function load() {
  loading.value = true
  try {
    if (isNew.value) {
      products.value = (await api.products()).data
    } else {
      const d = (await api.adminDeals()).find((x) => x.id === id.value)
      if (d) {
        form.product_id = d.product_id
        form.percent_off = d.percent_off
        form.active = d.active
        productName.value = d.product_name
        window.starts_at = d.starts_at
        window.ends_at = d.ends_at
      }
    }
  } catch {
    error.value = t('common.load_error')
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  error.value = null
  try {
    if (id.value === null) {
      if (form.product_id == null) return
      const now = new Date()
      const ends = new Date(now.getTime() + form.hours * 3600 * 1000)
      await api.createDeal({
        product_id: form.product_id,
        percent_off: form.percent_off,
        starts_at: now.toISOString(),
        ends_at: ends.toISOString(),
        active: true
      })
    } else {
      await api.updateDeal(id.value, {
        percent_off: form.percent_off,
        active: form.active
      })
    }
    router.push('/admin/deals')
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
    :title="isNew ? t('deals.new') : productName || t('nav.deals')"
    back-to="/admin/deals"
    :back-label="t('nav.deals')"
    :save-label="saving ? t('common.saving') : t('common.save')"
    :saving="saving"
    :disabled="saving || (isNew && form.product_id == null)"
    @save="save"
  >
    <div class="ecard">
      <h2>{{ t('nav.deals') }}</h2>
      <p v-if="error" class="notice" role="alert">{{ error }}</p>
      <div class="form">
        <label class="fld">
          <span>{{ t('products.product') }}</span>
          <Select
            v-if="isNew"
            v-model="form.product_id"
            :options="productOptions"
            option-label="label"
            option-value="id"
            filter
          />
          <strong v-else class="readonly">{{ productName }}</strong>
        </label>
        <label class="fld">
          <span>{{ t('deals.percent') }}</span>
          <InputNumber v-model="form.percent_off" :min="1" :max="90" suffix="%" />
        </label>
        <label v-if="isNew" class="fld">
          <span>{{ t('deals.duration') }}</span>
          <InputNumber v-model="form.hours" :min="1" :max="720" :suffix="` ${t('deal.hrs')}`" />
        </label>
        <template v-else>
          <label class="fld">
            <span>{{ t('deals.window') }}</span>
            <span class="readonly muted">{{ when(window.starts_at) }} → {{ when(window.ends_at) }}</span>
          </label>
          <label class="fld fld--row">
            <span>{{ t('common.status') }}</span>
            <ToggleSwitch v-model="form.active" />
          </label>
        </template>
      </div>
    </div>
  </EditorPage>
</template>

<style scoped>
.readonly {
  padding: 6px 0;
  font-weight: 600;
}
</style>
