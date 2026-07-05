<script setup lang="ts">
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError, type AdminCategory, api } from '../api'
import { t } from '../locale'
import EditorPage from '../components/EditorPage.vue'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.params.id === 'new')
const id = computed(() => (isNew.value ? null : Number(route.params.id)))

const LOCALES = ['en', 'fr', 'ar'] as const
type Loc = (typeof LOCALES)[number]
const activeLoc = ref<Loc>('en')

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const all = ref<AdminCategory[]>([])
const form = reactive({
  names: { en: '', fr: '', ar: '' } as Record<Loc, string>,
  parent_id: null as number | null,
  published: true
})

const parentOptions = computed(() => [
  { id: null as number | null, label: t('categories.no_parent') },
  ...all.value
    .filter((c) => c.id !== id.value)
    .map((c) => ({ id: c.id as number | null, label: catName(c) }))
])

function catName(c: AdminCategory): string {
  return c.translations.find((tr) => tr.locale === 'en')?.name ?? c.slug
}

async function load() {
  loading.value = true
  try {
    all.value = (await api.adminCategories()).data
    const c = all.value.find((x) => x.id === id.value)
    if (c) {
      for (const loc of LOCALES) {
        form.names[loc] = c.translations.find((tr) => tr.locale === loc)?.name ?? ''
      }
      form.parent_id = c.parent_id ?? null
      form.published = c.published ?? true
    }
  } catch {
    error.value = t('common.load_error')
  } finally {
    loading.value = false
  }
}

function translationsPayload() {
  const payload: Record<string, { name: string }> = { en: { name: form.names.en } }
  if (form.names.fr.trim()) payload.fr = { name: form.names.fr }
  if (form.names.ar.trim()) payload.ar = { name: form.names.ar }
  return payload
}

async function save() {
  saving.value = true
  error.value = null
  try {
    if (id.value === null) {
      await api.createCategory({
        translations: translationsPayload(),
        parent_id: form.parent_id,
        published: form.published
      })
    } else {
      await api.updateCategory(id.value, {
        translations: translationsPayload(),
        parent_id: form.parent_id ?? undefined,
        published: form.published
      })
    }
    router.push('/admin/categories')
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
    :title="isNew ? t('categories.new') : form.names.en || t('nav.categories')"
    back-to="/admin/categories"
    :back-label="t('nav.categories')"
    :save-label="saving ? t('common.saving') : t('common.save')"
    :saving="saving"
    :disabled="saving || !form.names.en.trim()"
    @save="save"
  >
    <div class="ecard">
      <h2>{{ t('categories.category') }}</h2>
      <p v-if="error" class="notice" role="alert">{{ error }}</p>
      <div class="locs" role="tablist" :aria-label="t('pedit.content_lang')">
        <button
          v-for="loc in LOCALES"
          :key="loc"
          type="button"
          role="tab"
          class="locs__tab"
          :class="{ on: activeLoc === loc }"
          :aria-selected="activeLoc === loc"
          @click="activeLoc = loc"
        >
          {{ loc.toUpperCase() }}
          <span v-if="loc !== 'en' && !form.names[loc]" class="locs__todo">·</span>
        </button>
      </div>
      <div class="form">
        <label class="fld">
          <span>{{ t('pedit.name') }} ({{ activeLoc }})</span>
          <InputText v-model="form.names[activeLoc]" :dir="activeLoc === 'ar' ? 'rtl' : 'ltr'" />
        </label>
        <label class="fld">
          <span>{{ t('categories.parent') }}</span>
          <Select
            v-model="form.parent_id"
            :options="parentOptions"
            option-label="label"
            option-value="id"
          />
        </label>
        <label class="fld fld--row">
          <span>{{ t('categories.published') }}</span>
          <ToggleSwitch v-model="form.published" />
        </label>
      </div>
    </div>
  </EditorPage>
</template>
