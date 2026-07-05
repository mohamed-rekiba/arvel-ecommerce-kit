<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { onMounted, reactive, ref } from 'vue'
import { type AdminBanner, ApiError, api } from '../api'
import { t } from '../locale'

const banners = ref<AdminBanner[]>([])
const loading = ref(true)
const notice = ref<string | null>(null)
const dialogOpen = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)

const LOCALES = ['en', 'fr', 'ar'] as const
type Loc = (typeof LOCALES)[number]
const activeLoc = ref<Loc>('en')

const empty = () => ({ title: '', subtitle: '', chip: '', cta_label: '' })
const form = reactive({
  copy: { en: empty(), fr: empty(), ar: empty() } as Record<Loc, ReturnType<typeof empty>>,
  cta_to: '/catalog',
  sort: 0,
  active: true
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

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    copy: { en: empty(), fr: empty(), ar: empty() },
    cta_to: '/catalog',
    sort: 0,
    active: true
  })
  activeLoc.value = 'en'
  dialogOpen.value = true
}

function openEdit(banner: AdminBanner) {
  editingId.value = banner.id
  const copy = { en: empty(), fr: empty(), ar: empty() } as Record<Loc, ReturnType<typeof empty>>
  for (const loc of LOCALES) {
    const text = banner.translations[loc]
    if (text)
      copy[loc] = {
        title: text.title,
        subtitle: text.subtitle ?? '',
        chip: text.chip ?? '',
        cta_label: text.cta_label ?? ''
      }
  }
  Object.assign(form, {
    copy,
    cta_to: banner.cta_to,
    sort: banner.sort,
    active: banner.active
  })
  activeLoc.value = 'en'
  dialogOpen.value = true
}

function payloadTranslations() {
  const out: Record<
    string,
    {
      title: string
      subtitle?: string | null
      chip?: string | null
      cta_label?: string | null
    }
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
  notice.value = null
  try {
    const body = {
      translations: payloadTranslations(),
      cta_to: form.cta_to,
      sort: form.sort,
      active: form.active
    }
    if (editingId.value === null) await api.createBanner(body)
    else await api.updateBanner(editingId.value, body)
    dialogOpen.value = false
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

async function toggleActive(banner: AdminBanner) {
  try {
    const updated = await api.updateBanner(banner.id, {
      active: !banner.active
    })
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

async function onUpload(banner: AdminBanner, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  notice.value = null
  try {
    const updated = await api.uploadBannerImage(banner.id, file)
    banners.value = banners.value.map((b) => (b.id === updated.id ? updated : b))
  } catch {
    notice.value = t('banners.upload_error')
  } finally {
    input.value = ''
  }
}

onMounted(load)
</script>

<template>
  <section class="page">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('reviews.eyebrow') }}</p>
        <h1>{{ t('nav.banners') }}</h1>
        <p class="sub">{{ t('banners.sub') }}</p>
      </div>
      <Button :label="t('banners.new')" icon="pi pi-plus" @click="openCreate" />
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="banners" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty
          ><p class="empty">{{ t('banners.none') }}</p></template
        >
        <Column :header="t('banners.image')" style="width: 9rem">
          <template #body="{ data }">
            <img v-if="data.image_url" class="thumb" :src="data.image_url" alt="" />
            <span v-else class="muted">—</span>
          </template>
        </Column>
        <Column :header="t('banners.slide')">
          <template #body="{ data }">
            <div class="pname">{{ data.translations.en?.title ?? '—' }}</div>
            <div class="muted">
              {{ data.cta_to }} ·
              {{ Object.keys(data.translations).join(', ') }}
            </div>
          </template>
        </Column>
        <Column :header="t('banners.sort')" style="width: 5rem">
          <template #body="{ data }">{{ data.sort }}</template>
        </Column>
        <Column :header="t('common.status')" style="width: 7rem">
          <template #body="{ data }">
            <Tag
              :value="data.active ? t('banners.live') : t('deals.paused')"
              :severity="data.active ? 'success' : 'secondary'"
            />
          </template>
        </Column>
        <Column header="" style="width: 16rem">
          <template #body="{ data }">
            <label class="upl">
              <input type="file" accept="image/*" @change="onUpload(data, $event)" />
              <span>{{ t('banners.upload') }}</span>
            </label>
            <Button size="small" text :label="t('common.edit')" @click="openEdit(data)" />
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

    <Dialog
      v-model:visible="dialogOpen"
      modal
      :header="editingId === null ? t('banners.new') : t('banners.edit')"
      :style="{ width: '30rem' }"
    >
      <form class="form" @submit.prevent="save">
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
        <label class="field"
          ><span>{{ t('banners.title') }} ({{ activeLoc }})</span>
          <InputText
            v-model="form.copy[activeLoc].title"
            :dir="activeLoc === 'ar' ? 'rtl' : 'ltr'"
            :required="activeLoc === 'en'"
          />
        </label>
        <label class="field"
          ><span>{{ t('banners.subtitle') }} ({{ activeLoc }})</span>
          <InputText
            v-model="form.copy[activeLoc].subtitle"
            :dir="activeLoc === 'ar' ? 'rtl' : 'ltr'"
          />
        </label>
        <div class="row">
          <label class="field"
            ><span>{{ t('banners.chip') }} ({{ activeLoc }})</span>
            <InputText
              v-model="form.copy[activeLoc].chip"
              :dir="activeLoc === 'ar' ? 'rtl' : 'ltr'"
            />
          </label>
          <label class="field"
            ><span>{{ t('banners.cta_label') }} ({{ activeLoc }})</span>
            <InputText
              v-model="form.copy[activeLoc].cta_label"
              :dir="activeLoc === 'ar' ? 'rtl' : 'ltr'"
            />
          </label>
        </div>
        <div class="row">
          <label class="field"
            ><span>{{ t('banners.cta_to') }}</span>
            <InputText v-model="form.cta_to" dir="ltr" />
          </label>
          <label class="field"
            ><span>{{ t('banners.sort') }}</span>
            <InputNumber v-model="form.sort" :min="0" :max="99" />
          </label>
        </div>
        <label class="field field--switch"
          ><span>{{ t('banners.live') }}</span
          ><ToggleSwitch v-model="form.active"
        /></label>
        <Button
          type="submit"
          :label="saving ? t('common.saving') : t('common.save')"
          :disabled="saving || !form.copy.en.title"
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
  font-size: 12px;
}
.thumb {
  width: 110px;
  aspect-ratio: 16 / 7;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}
.empty {
  text-align: center;
  color: var(--text-subtle);
  padding: 24px 0;
}
.upl {
  display: inline-flex;
  align-items: center;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--border-2);
  border-radius: var(--radius-sm);
  padding: 5px 10px;
  font-size: 12px;
  cursor: pointer;
  margin-inline-end: 6px;
}
.upl input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}
.locs {
  display: inline-flex;
  gap: 4px;
  margin-bottom: var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 2px;
}
.locs__tab {
  border: 0;
  background: none;
  font: inherit;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-muted);
}
.locs__tab.on {
  background: var(--text);
  color: var(--bg);
}
.locs__todo {
  color: var(--warn);
  font-weight: 700;
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
.field :deep(input) {
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
