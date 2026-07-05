<script setup lang="ts">
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError, api } from '../api'
import { t } from '../locale'
import EditorPage from '../components/EditorPage.vue'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.params.id === 'new')
const id = computed(() => (isNew.value ? null : Number(route.params.id)))

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const form = reactive({ name: '', published: true })

async function load() {
  loading.value = true
  try {
    if (id.value !== null) {
      const v = (await api.vendors()).find((x) => x.id === id.value)
      if (v) Object.assign(form, { name: v.name, published: v.published })
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
    if (id.value === null) await api.createVendor({ name: form.name })
    else await api.updateVendor(id.value, { name: form.name, published: form.published })
    router.push('/admin/vendors')
  } catch (e) {
    error.value =
      e instanceof ApiError
        ? (Object.values(e.errors)[0]?.[0] ?? t('vendors.create_error'))
        : t('vendors.create_error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <EditorPage
    :title="isNew ? t('vendors.new_title') : form.name || t('nav.vendors')"
    back-to="/admin/vendors"
    :back-label="t('nav.vendors')"
    :save-label="saving ? t('common.saving') : t('common.save')"
    :saving="saving"
    :disabled="saving || !form.name.trim()"
    @save="save"
  >
    <div class="ecard">
      <h2>{{ t('vendors.vendor') }}</h2>
      <p v-if="error" class="notice" role="alert">{{ error }}</p>
      <div class="form">
        <label class="fld">
          <span>{{ t('vendors.name') }}</span>
          <InputText v-model="form.name" />
        </label>
        <label class="fld fld--row">
          <span>{{ t('categories.published') }}</span>
          <ToggleSwitch v-model="form.published" />
        </label>
      </div>
    </div>
  </EditorPage>
</template>
