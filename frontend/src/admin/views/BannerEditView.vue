<script setup lang="ts">
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { type AdminBanner, ApiError, api } from '../api'
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
const imageUrl = ref<string | null>(null)

const empty = () => ({ title: '', subtitle: '', chip: '', cta_label: '' })
const form = reactive({
  copy: { en: empty(), fr: empty(), ar: empty() } as Record<Loc, ReturnType<typeof empty>>,
  cta_to: '/catalog',
  sort: 0,
  active: true
})

async function load() {
  loading.value = true
  try {
    if (id.value !== null) {
      const b = (await api.adminBanners()).find((x) => x.id === id.value)
      if (b) hydrate(b)
    }
  } catch {
    error.value = t('common.load_error')
  } finally {
    loading.value = false
  }
}

function hydrate(b: AdminBanner) {
  for (const loc of LOCALES) {
    const text = b.translations[loc]
    if (text)
      form.copy[loc] = {
        title: text.title,
        subtitle: text.subtitle ?? '',
        chip: text.chip ?? '',
        cta_label: text.cta_label ?? ''
      }
  }
  form.cta_to = b.cta_to
  form.sort = b.sort
  form.active = b.active
  imageUrl.value = b.image_url ?? null
}

function payloadTranslations() {
  const out: Record<
    string,
    { title: string; subtitle?: string | null; chip?: string | null; cta_label?: string | null }
  > = {}
  for (const loc of LOCALES) {
    const c = form.copy[loc]
    if (c.title.trim()) {
      out[loc] = {
        title: c.title,
        subtitle: c.subtitle || null,
        chip: c.chip || null,
        cta_label: c.cta_label || null
      }
    }
  }
  return out
}

async function save() {
  saving.value = true
  error.value = null
  try {
    const body = {
      translations: payloadTranslations(),
      cta_to: form.cta_to,
      sort: form.sort,
      active: form.active
    }
    if (id.value === null) await api.createBanner(body)
    else await api.updateBanner(id.value, body)
    router.push('/admin/banners')
  } catch (e) {
    error.value =
      e instanceof ApiError
        ? (Object.values(e.errors)[0]?.[0] ?? t('common.save_error'))
        : t('common.save_error')
  } finally {
    saving.value = false
  }
}

async function onUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || id.value === null) return
  error.value = null
  try {
    const updated = await api.uploadBannerImage(id.value, file)
    imageUrl.value = updated.image_url ?? null
  } catch {
    error.value = t('banners.upload_error')
  } finally {
    input.value = ''
  }
}

onMounted(load)
</script>

<template>
  <EditorPage
    :title="isNew ? t('banners.new') : form.copy.en.title || t('nav.banners')"
    back-to="/admin/banners"
    :back-label="t('nav.banners')"
    :save-label="saving ? t('common.saving') : t('common.save')"
    :saving="saving"
    :disabled="saving || !form.copy.en.title.trim()"
    @save="save"
  >
    <div class="ecard">
      <h2>{{ t('banners.slide') }}</h2>
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
          <span v-if="loc !== 'en' && !form.copy[loc].title" class="locs__todo">·</span>
        </button>
      </div>
      <div class="form">
        <label class="fld">
          <span>{{ t('banners.title') }} ({{ activeLoc }})</span>
          <InputText
            v-model="form.copy[activeLoc].title"
            :dir="activeLoc === 'ar' ? 'rtl' : 'ltr'"
          />
        </label>
        <label class="fld">
          <span>{{ t('banners.subtitle') }} ({{ activeLoc }})</span>
          <InputText
            v-model="form.copy[activeLoc].subtitle"
            :dir="activeLoc === 'ar' ? 'rtl' : 'ltr'"
          />
        </label>
        <div class="frow">
          <label class="fld">
            <span>{{ t('banners.chip') }} ({{ activeLoc }})</span>
            <InputText
              v-model="form.copy[activeLoc].chip"
              :dir="activeLoc === 'ar' ? 'rtl' : 'ltr'"
            />
          </label>
          <label class="fld">
            <span>{{ t('banners.cta_label') }} ({{ activeLoc }})</span>
            <InputText
              v-model="form.copy[activeLoc].cta_label"
              :dir="activeLoc === 'ar' ? 'rtl' : 'ltr'"
            />
          </label>
        </div>
      </div>
    </div>

    <div class="ecard">
      <h2>{{ t('banners.placement') }}</h2>
      <div class="form">
        <div class="frow">
          <label class="fld">
            <span>{{ t('banners.cta_to') }}</span>
            <InputText v-model="form.cta_to" dir="ltr" />
          </label>
          <label class="fld">
            <span>{{ t('banners.sort') }}</span>
            <InputNumber v-model="form.sort" :min="0" :max="99" />
          </label>
        </div>
        <label class="fld fld--row">
          <span>{{ t('banners.live') }}</span>
          <ToggleSwitch v-model="form.active" />
        </label>
      </div>
    </div>

    <div class="ecard">
      <h2>{{ t('banners.image') }}</h2>
      <p v-if="isNew" class="ehint">{{ t('banners.image_after_save') }}</p>
      <template v-else>
        <img v-if="imageUrl" class="bthumb" :src="imageUrl" alt="" />
        <label class="upl">
          <input type="file" accept="image/*" @change="onUpload" />
          <span>{{ imageUrl ? t('banners.replace_image') : t('banners.upload') }}</span>
        </label>
      </template>
    </div>
  </EditorPage>
</template>

<style scoped>
.bthumb {
  display: block;
  width: 260px;
  max-width: 100%;
  aspect-ratio: 16 / 7;
  object-fit: cover;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  margin-bottom: 12px;
}
.upl {
  display: inline-flex;
  align-items: center;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--border-2);
  border-radius: var(--radius-sm);
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.upl input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}
</style>
