<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError, type GalleryImage, type Translate, type Variant, api, formatPrice } from '../api'
import { type MessageKey, t } from '../locale'
import EditorPage from '../components/EditorPage.vue'

const route = useRoute()
const router = useRouter()
const productId = computed(() => (route.params.id === 'new' ? null : Number(route.params.id)))
const isCreate = computed(() => productId.value === null)

const LOCALES = ['en', 'fr', 'ar'] as const
type Locale = (typeof LOCALES)[number]

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const fieldErrors = ref<Record<string, string[]>>({})
const notice = ref<string | null>(null)

const activeLocale = ref<Locale>('en')
const form = reactive({
  price_cents: 0,
  category_id: 1,
  status: 'draft',
  published: false,
  featured: false,
  translations: {
    en: { name: '', description: '' },
    fr: { name: '', description: '' },
    ar: { name: '', description: '' }
  } as Record<Locale, { name: string; description: string }>
})
const isVisible = ref(false)
const slug = ref('')
const variants = ref<Variant[]>([])
const gallery = ref<GalleryImage[]>([])
const categories = ref<{ id: number; label: string }[]>([])

const newVariant = reactive({
  sku: '',
  name: '',
  price_adjustment_cents: 0,
  stock: 0
})
const stockDrafts = reactive<Record<number, number>>({})

const STATUSES = [
  { value: 'draft', label: t('pstatus.draft') },
  { value: 'active', label: t('pstatus.active') },
  { value: 'archived', label: t('pstatus.archived') }
]

function catName(translations: Translate[]): string {
  return translations.find((t) => t.locale === 'en')?.name ?? '—'
}

function fail(e: unknown, fallback: string) {
  if (e instanceof ApiError && Object.keys(e.errors).length > 0) {
    fieldErrors.value = e.errors
    error.value = t('pedit.check_fields')
  } else {
    error.value = fallback
  }
}

function firstError(...keys: string[]): string | null {
  for (const key of keys) {
    const messages = fieldErrors.value[key]
    if (messages?.length) return messages[0]
  }
  return null
}

async function load() {
  loading.value = true
  try {
    const cats = await api.categories()
    categories.value = cats.data.map((c) => ({
      id: c.id,
      label: catName(c.translations)
    }))
    if (productId.value !== null) {
      const detail = await api.productDetail(productId.value)
      form.price_cents = detail.price_cents
      form.category_id = detail.category_id
      form.status = detail.status
      form.published = detail.published
      form.featured = detail.featured
      for (const tr of detail.translations) {
        if (tr.locale && (LOCALES as readonly string[]).includes(tr.locale)) {
          form.translations[tr.locale as Locale] = {
            name: tr.name,
            description: tr.description ?? ''
          }
        }
      }
      isVisible.value = detail.is_visible
      slug.value = detail.slug
      variants.value = detail.variants
      gallery.value = detail.gallery
      for (const v of detail.variants) stockDrafts[v.id] = v.stock
    }
  } catch {
    error.value = t('pedit.load_error')
  } finally {
    loading.value = false
  }
}

function translationsPayload() {
  const payload: Record<string, { name: string; description: string | null }> = {
    en: {
      name: form.translations.en.name,
      description: form.translations.en.description || null
    }
  }
  for (const code of ['fr', 'ar'] as const) {
    if (form.translations[code].name.trim()) {
      payload[code] = {
        name: form.translations[code].name,
        description: form.translations[code].description || null
      }
    }
  }
  return payload
}

async function save() {
  saving.value = true
  error.value = null
  fieldErrors.value = {}
  notice.value = null
  try {
    if (isCreate.value) {
      const created = await api.createProduct({
        category_id: form.category_id,
        price_cents: form.price_cents,
        translations: translationsPayload()
      })
      await router.replace(`/admin/products/${created.id}`)
      notice.value = t('pedit.created')
      await load()
    } else {
      await api.updateProduct(productId.value as number, {
        category_id: form.category_id,
        price_cents: form.price_cents,
        status: form.status,
        published: form.published,
        featured: form.featured,
        translations: translationsPayload()
      })
      notice.value = t('pedit.saved')
      await load()
    }
  } catch (e) {
    fail(e, t('pedit.save_error'))
  } finally {
    saving.value = false
  }
}

async function addVariant() {
  error.value = null
  fieldErrors.value = {}
  try {
    const created = await api.createVariant(productId.value as number, {
      ...newVariant
    })
    variants.value = [...variants.value, created]
    stockDrafts[created.id] = created.stock
    Object.assign(newVariant, {
      sku: '',
      name: '',
      price_adjustment_cents: 0,
      stock: 0
    })
  } catch (e) {
    fail(e, t('pedit.variant_error'))
  }
}

async function setStock(variant: Variant) {
  error.value = null
  try {
    const updated = await api.adjustStock(productId.value as number, variant.id, {
      set: stockDrafts[variant.id],
      reason: 'manual adjustment (admin console)'
    })
    variants.value = variants.value.map((v) => (v.id === updated.id ? updated : v))
    stockDrafts[updated.id] = updated.stock
  } catch (e) {
    fail(e, t('pedit.stock_error'))
  }
}

async function removeVariant(variant: Variant) {
  if (!window.confirm(t('pedit.variant_delete_confirm', { sku: variant.sku }))) return
  error.value = null
  try {
    await api.deleteVariant(productId.value as number, variant.id)
    variants.value = variants.value.filter((v) => v.id !== variant.id)
  } catch (e) {
    fail(e, t('pedit.variant_ordered'))
  }
}

async function onUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  error.value = null
  try {
    gallery.value = await api.uploadImage(productId.value as number, file)
  } catch (e) {
    fail(e, t('pedit.upload_error'))
  } finally {
    input.value = ''
  }
}

async function removeImage(image: GalleryImage) {
  if (!window.confirm(t('pedit.image_confirm'))) return
  try {
    gallery.value = await api.deleteImage(productId.value as number, image.id)
  } catch {
    error.value = t('pedit.image_error')
  }
}

onMounted(load)
</script>

<template>
  <EditorPage
    :title="isCreate ? t('products.new') : form.translations.en.name || slug"
    back-to="/admin/products"
    :back-label="t('nav.products')"
    :save-label="
      saving ? t('common.saving') : isCreate ? t('pedit.create') : t('pedit.save_changes')
    "
    :saving="saving"
    :disabled="saving || !form.translations.en.name.trim()"
    @save="save"
  >
    <template #badges>
      <template v-if="!isCreate">
        <Tag
          :value="t(`pstatus.${form.status}` as MessageKey)"
          :severity="form.status === 'active' ? 'success' : 'secondary'"
        />
        <Tag
          :value="isVisible ? t('pedit.visible') : t('pedit.hidden')"
          :severity="isVisible ? 'success' : 'warn'"
        />
      </template>
    </template>

    <p v-if="loading" class="ehint">{{ t('common.loading') }}</p>

    <template v-else>
      <!-- details -->
      <div class="ecard">
        <h2>{{ t('pedit.details') }}</h2>
        <p v-if="error" class="notice" role="alert">{{ error }}</p>
        <p v-if="notice" class="eok" role="status">{{ notice }}</p>

        <div class="locs" role="tablist" :aria-label="t('pedit.content_lang')">
          <button
            v-for="code in LOCALES"
            :key="code"
            type="button"
            role="tab"
            class="locs__tab"
            :class="{ on: activeLocale === code }"
            :aria-selected="activeLocale === code"
            @click="activeLocale = code"
          >
            {{ code.toUpperCase() }}
            <span v-if="code !== 'en' && !form.translations[code].name" class="locs__todo">·</span>
          </button>
        </div>

        <div class="form">
          <label class="fld">
            <span>{{ t('pedit.name') }} ({{ activeLocale }})</span>
            <InputText
              v-model="form.translations[activeLocale].name"
              :dir="activeLocale === 'ar' ? 'rtl' : 'ltr'"
              :invalid="!!firstError('translations')"
            />
          </label>
          <label class="fld">
            <span>{{ t('pedit.description') }} ({{ activeLocale }})</span>
            <Textarea
              v-model="form.translations[activeLocale].description"
              :dir="activeLocale === 'ar' ? 'rtl' : 'ltr'"
              rows="3"
              auto-resize
            />
          </label>
          <small v-if="firstError('translations')" class="err" role="alert">{{
            firstError('translations')
          }}</small>

          <div class="frow">
            <label class="fld">
              <span>{{ t('pedit.price') }}</span>
              <InputNumber
                v-model="form.price_cents"
                :use-grouping="false"
                :min="0"
                :invalid="!!firstError('price_cents')"
              />
            </label>
            <label class="fld">
              <span>{{ t('categories.category') }}</span>
              <Select
                v-model="form.category_id"
                :options="categories"
                option-label="label"
                option-value="id"
              />
            </label>
          </div>

          <div class="frow">
            <label class="fld">
              <span>{{ t('common.status') }}</span>
              <Select
                v-model="form.status"
                :options="STATUSES"
                option-label="label"
                option-value="value"
                :disabled="isCreate"
              />
            </label>
            <div class="switches">
              <label class="fld fld--row">
                <span>{{ t('categories.published') }}</span>
                <ToggleSwitch v-model="form.published" :disabled="isCreate" />
              </label>
              <label class="fld fld--row">
                <span>{{ t('pedit.featured') }}</span>
                <ToggleSwitch v-model="form.featured" :disabled="isCreate" />
              </label>
            </div>
          </div>
          <p v-if="isCreate" class="ehint">{{ t('pedit.after_save_hint') }}</p>
        </div>
      </div>

      <!-- variants -->
      <div class="ecard">
        <h2>{{ t('pedit.variants') }}</h2>
        <p v-if="isCreate" class="ehint">{{ t('pedit.variants_after_save') }}</p>
        <template v-else>
          <DataTable :value="variants" data-key="id" size="small">
            <template #empty>
              <p class="empty">{{ t('pedit.no_variants') }}</p>
            </template>
            <Column field="sku" :header="t('pedit.sku')" />
            <Column field="name" :header="t('pedit.name')" />
            <Column :header="t('pedit.price_adj')">
              <template #body="{ data }">{{ formatPrice(data.price_adjustment_cents) }}</template>
            </Column>
            <Column :header="t('pedit.stock')">
              <template #body="{ data }">
                <div class="stockset">
                  <InputNumber
                    v-model="stockDrafts[data.id]"
                    :use-grouping="false"
                    :min="0"
                    size="small"
                  />
                  <Button
                    size="small"
                    severity="secondary"
                    outlined
                    :label="t('pedit.set')"
                    :disabled="stockDrafts[data.id] === data.stock"
                    @click="setStock(data)"
                  />
                </div>
              </template>
            </Column>
            <Column header="">
              <template #body="{ data }">
                <Button
                  size="small"
                  severity="danger"
                  text
                  :label="t('common.delete')"
                  @click="removeVariant(data)"
                />
              </template>
            </Column>
          </DataTable>
          <small v-if="firstError('sku', 'stock', 'variant')" class="err" role="alert">
            {{ firstError('sku', 'stock', 'variant') }}
          </small>
          <form class="variant-add" @submit.prevent="addVariant">
            <InputText v-model="newVariant.sku" :placeholder="t('pedit.sku')" />
            <InputText v-model="newVariant.name" :placeholder="t('pedit.name')" />
            <InputNumber
              v-model="newVariant.price_adjustment_cents"
              :use-grouping="false"
              :placeholder="t('pedit.adj_ph')"
            />
            <InputNumber
              v-model="newVariant.stock"
              :use-grouping="false"
              :min="0"
              :placeholder="t('pedit.stock')"
            />
            <Button
              type="submit"
              size="small"
              :label="t('pedit.add_variant')"
              :disabled="!newVariant.sku || !newVariant.name"
            />
          </form>
        </template>
      </div>

      <!-- gallery -->
      <div class="ecard">
        <h2>{{ t('pedit.gallery') }}</h2>
        <p v-if="isCreate" class="ehint">{{ t('pedit.gallery_after_save') }}</p>
        <template v-else>
          <div class="gallery">
            <figure v-for="image in gallery" :key="image.id" class="gallery__item">
              <img :src="image.thumb_url" alt="" />
              <Button
                size="small"
                severity="danger"
                text
                :label="t('pedit.remove')"
                @click="removeImage(image)"
              />
            </figure>
            <label class="gallery__add">
              <input type="file" accept="image/*" @change="onUpload" />
              <span>+ {{ t('pedit.upload') }}</span>
            </label>
          </div>
          <small v-if="firstError('image')" class="err" role="alert">{{
            firstError('image')
          }}</small>
        </template>
      </div>
    </template>
  </EditorPage>
</template>

<style scoped>
.switches {
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: center;
}
.err {
  color: var(--danger-fg);
  font-size: 12.5px;
  display: block;
  margin: 6px 0;
}
.stockset {
  display: flex;
  gap: 8px;
  align-items: center;
}
.stockset :deep(input) {
  width: 90px;
}
.variant-add {
  display: grid;
  grid-template-columns: 1fr 1fr 120px 120px auto;
  gap: 8px;
  margin-top: 14px;
}
.variant-add :deep(input) {
  width: 100%;
}
.gallery {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}
.gallery__item {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.gallery__item img {
  width: 96px;
  height: 96px;
  object-fit: cover;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
}
.gallery__add {
  display: grid;
  place-items: center;
  width: 96px;
  height: 96px;
  border: 1px dashed var(--border-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 12px;
  color: var(--text-muted);
}
.gallery__add input {
  display: none;
}
@media (max-width: 720px) {
  .variant-add {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
