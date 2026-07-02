<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Tag from "primevue/tag";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ApiError,
  type GalleryImage,
  type Translate,
  type Variant,
  api,
  formatPrice,
} from "../api";

const route = useRoute();
const router = useRouter();
const productId = computed(() =>
  route.params.id === "new" ? null : Number(route.params.id),
);
const isCreate = computed(() => productId.value === null);

const LOCALES = ["en", "fr"] as const;
type Locale = (typeof LOCALES)[number];

const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(null);
const fieldErrors = ref<Record<string, string[]>>({});
const notice = ref<string | null>(null);

const activeLocale = ref<Locale>("en");
const form = reactive({
  price_cents: 0,
  category_id: 1,
  status: "draft",
  published: false,
  translations: {
    en: { name: "", description: "" },
    fr: { name: "", description: "" },
  } as Record<Locale, { name: string; description: string }>,
});
const isVisible = ref(false);
const slug = ref("");
const variants = ref<Variant[]>([]);
const gallery = ref<GalleryImage[]>([]);
const categories = ref<{ id: number; label: string }[]>([]);

const newVariant = reactive({ sku: "", name: "", price_adjustment_cents: 0, stock: 0 });
const stockDrafts = reactive<Record<number, number>>({});

const STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "active", label: "Active" },
  { value: "archived", label: "Archived" },
];

function catName(translations: Translate[]): string {
  return translations.find((t) => t.locale === "en")?.name ?? "—";
}

function fail(e: unknown, fallback: string) {
  if (e instanceof ApiError && Object.keys(e.errors).length > 0) {
    fieldErrors.value = e.errors;
    error.value = "Please check the highlighted fields.";
  } else {
    error.value = fallback;
  }
}

function firstError(...keys: string[]): string | null {
  for (const key of keys) {
    const messages = fieldErrors.value[key];
    if (messages?.length) return messages[0];
  }
  return null;
}

async function load() {
  loading.value = true;
  try {
    const cats = await api.categories();
    categories.value = cats.data.map((c) => ({ id: c.id, label: catName(c.translations) }));
    if (productId.value !== null) {
      const detail = await api.productDetail(productId.value);
      form.price_cents = detail.price_cents;
      form.category_id = detail.category_id;
      form.status = detail.status;
      form.published = detail.published;
      for (const t of detail.translations) {
        if (t.locale === "en" || t.locale === "fr") {
          form.translations[t.locale] = { name: t.name, description: t.description ?? "" };
        }
      }
      isVisible.value = detail.is_visible;
      slug.value = detail.slug;
      variants.value = detail.variants;
      gallery.value = detail.gallery;
      for (const v of detail.variants) stockDrafts[v.id] = v.stock;
    }
  } catch {
    error.value = "Couldn't load the product.";
  } finally {
    loading.value = false;
  }
}

function translationsPayload() {
  const payload: Record<string, { name: string; description: string | null }> = {
    en: {
      name: form.translations.en.name,
      description: form.translations.en.description || null,
    },
  };
  if (form.translations.fr.name.trim()) {
    payload.fr = {
      name: form.translations.fr.name,
      description: form.translations.fr.description || null,
    };
  }
  return payload;
}

async function save() {
  saving.value = true;
  error.value = null;
  fieldErrors.value = {};
  notice.value = null;
  try {
    if (isCreate.value) {
      const created = await api.createProduct({
        category_id: form.category_id,
        price_cents: form.price_cents,
        translations: translationsPayload(),
      });
      await router.replace(`/admin/products/${created.id}`);
      notice.value = "Product created.";
      await load();
    } else {
      await api.updateProduct(productId.value as number, {
        category_id: form.category_id,
        price_cents: form.price_cents,
        status: form.status,
        published: form.published,
        translations: translationsPayload(),
      });
      notice.value = "Saved.";
      await load();
    }
  } catch (e) {
    fail(e, "Couldn't save the product.");
  } finally {
    saving.value = false;
  }
}

async function addVariant() {
  error.value = null;
  fieldErrors.value = {};
  try {
    const created = await api.createVariant(productId.value as number, { ...newVariant });
    variants.value = [...variants.value, created];
    stockDrafts[created.id] = created.stock;
    Object.assign(newVariant, { sku: "", name: "", price_adjustment_cents: 0, stock: 0 });
  } catch (e) {
    fail(e, "Couldn't add the variant.");
  }
}

async function setStock(variant: Variant) {
  error.value = null;
  try {
    const updated = await api.adjustStock(variant.id, {
      set: stockDrafts[variant.id],
      reason: "manual adjustment (admin console)",
    });
    variants.value = variants.value.map((v) => (v.id === updated.id ? updated : v));
    stockDrafts[updated.id] = updated.stock;
  } catch (e) {
    fail(e, "Couldn't adjust stock.");
  }
}

async function removeVariant(variant: Variant) {
  if (!window.confirm(`Delete variant ${variant.sku}?`)) return;
  error.value = null;
  try {
    await api.deleteVariant(variant.id);
    variants.value = variants.value.filter((v) => v.id !== variant.id);
  } catch (e) {
    fail(e, "This variant has been ordered — it can't be deleted.");
  }
}

async function onUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  error.value = null;
  try {
    gallery.value = await api.uploadImage(productId.value as number, file);
  } catch (e) {
    fail(e, "That file couldn't be uploaded (images only).");
  } finally {
    input.value = "";
  }
}

async function removeImage(image: GalleryImage) {
  if (!window.confirm("Remove this image?")) return;
  try {
    gallery.value = await api.deleteImage(productId.value as number, image.id);
  } catch {
    error.value = "Couldn't remove the image.";
  }
}

onMounted(load);
</script>

<template>
  <section class="edit">
    <header class="edit__head">
      <div>
        <RouterLink class="edit__back" to="/admin/products">← Products</RouterLink>
        <h1>{{ isCreate ? "New product" : form.translations.en.name || slug }}</h1>
      </div>
      <div class="edit__badges" v-if="!isCreate">
        <Tag :value="form.status" :severity="form.status === 'active' ? 'success' : 'secondary'" />
        <Tag
          :value="isVisible ? 'visible on storefront' : 'hidden'"
          :severity="isVisible ? 'success' : 'warn'"
        />
      </div>
    </header>

    <p v-if="loading">Loading…</p>

    <template v-else>
      <form class="card" @submit.prevent="save">
        <h2>Details</h2>

        <div class="locales" role="tablist" aria-label="Content language">
          <button
            v-for="code in LOCALES"
            :key="code"
            type="button"
            role="tab"
            class="locales__tab"
            :class="{ on: activeLocale === code }"
            :aria-selected="activeLocale === code"
            @click="activeLocale = code"
          >
            {{ code.toUpperCase() }}
            <span v-if="code === 'fr' && !form.translations.fr.name" class="locales__todo">·</span>
          </button>
        </div>

        <label class="field">
          <span>Name ({{ activeLocale }})</span>
          <InputText v-model="form.translations[activeLocale].name" :invalid="!!firstError('translations')" />
        </label>
        <label class="field">
          <span>Description ({{ activeLocale }})</span>
          <Textarea v-model="form.translations[activeLocale].description" rows="3" autoResize />
        </label>
        <small v-if="firstError('translations')" class="err" role="alert">{{ firstError("translations") }}</small>

        <div class="row">
          <label class="field">
            <span>Price (cents)</span>
            <InputNumber v-model="form.price_cents" :useGrouping="false" :min="0" :invalid="!!firstError('price_cents')" />
          </label>
          <label class="field">
            <span>Category</span>
            <Select v-model="form.category_id" :options="categories" optionLabel="label" optionValue="id" />
          </label>
          <label class="field" v-if="!isCreate">
            <span>Status</span>
            <Select v-model="form.status" :options="STATUSES" optionLabel="label" optionValue="value" />
          </label>
          <label class="field field--switch" v-if="!isCreate">
            <span>Published</span>
            <ToggleSwitch v-model="form.published" />
          </label>
        </div>

        <p v-if="error" class="err" role="alert">{{ error }}</p>
        <p v-if="notice" class="ok" role="status">{{ notice }}</p>
        <Button type="submit" :label="saving ? 'Saving…' : isCreate ? 'Create product' : 'Save changes'" :disabled="saving" />
      </form>

      <section v-if="!isCreate" class="card">
        <h2>Variants &amp; stock</h2>
        <DataTable :value="variants" dataKey="id" size="small">
          <Column field="sku" header="SKU" />
          <Column field="name" header="Name" />
          <Column header="Price adj.">
            <template #body="{ data }">{{ formatPrice(data.price_adjustment_cents) }}</template>
          </Column>
          <Column header="Stock">
            <template #body="{ data }">
              <div class="stock">
                <InputNumber v-model="stockDrafts[data.id]" :useGrouping="false" :min="0" size="small" />
                <Button
                  size="small"
                  severity="secondary"
                  outlined
                  label="Set"
                  :disabled="stockDrafts[data.id] === data.stock"
                  @click="setStock(data)"
                />
              </div>
            </template>
          </Column>
          <Column header="">
            <template #body="{ data }">
              <Button size="small" severity="danger" text label="Delete" @click="removeVariant(data)" />
            </template>
          </Column>
        </DataTable>
        <small v-if="firstError('sku', 'stock', 'variant')" class="err" role="alert">
          {{ firstError("sku", "stock", "variant") }}
        </small>
        <form class="variant-add" @submit.prevent="addVariant">
          <InputText v-model="newVariant.sku" placeholder="SKU" />
          <InputText v-model="newVariant.name" placeholder="Name" />
          <InputNumber v-model="newVariant.price_adjustment_cents" :useGrouping="false" placeholder="Adj. ¢" />
          <InputNumber v-model="newVariant.stock" :useGrouping="false" :min="0" placeholder="Stock" />
          <Button type="submit" size="small" label="Add variant" :disabled="!newVariant.sku || !newVariant.name" />
        </form>
      </section>

      <section v-if="!isCreate" class="card">
        <h2>Gallery</h2>
        <div class="gallery">
          <figure v-for="image in gallery" :key="image.id" class="gallery__item">
            <img :src="image.thumb_url" alt="" />
            <Button size="small" severity="danger" text label="Remove" @click="removeImage(image)" />
          </figure>
          <label class="gallery__add">
            <input type="file" accept="image/*" @change="onUpload" />
            <span>+ Upload image</span>
          </label>
        </div>
        <small v-if="firstError('image')" class="err" role="alert">{{ firstError("image") }}</small>
      </section>
    </template>
  </section>
</template>

<style scoped>
.edit__head { display: flex; justify-content: space-between; align-items: start; margin-bottom: var(--space-6); gap: var(--space-4); }
.edit__back { font-size: var(--text-sm); color: var(--color-text-muted); text-decoration: none; }
.edit__head h1 { margin: var(--space-2) 0 0; font-size: var(--text-2xl); }
.edit__badges { display: flex; gap: var(--space-2); }
.card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-6); margin-bottom: var(--space-6); }
.card h2 { font-size: var(--text-sm); text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-muted); margin: 0 0 var(--space-4); }
.locales { display: inline-flex; gap: var(--space-1); margin-bottom: var(--space-4); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 2px; }
.locales__tab { border: 0; background: none; font: inherit; padding: var(--space-1) var(--space-3); border-radius: var(--radius-sm); cursor: pointer; color: var(--color-text-muted); }
.locales__tab.on { background: var(--color-text); color: var(--color-bg); }
.locales__todo { color: var(--color-warning, #b45309); font-weight: 700; }
.field { display: block; margin-bottom: var(--space-4); }
.field span { display: block; font-size: var(--text-sm); margin-bottom: var(--space-1); }
.field :deep(input), .field :deep(textarea) { width: 100%; }
.field--switch { display: flex; align-items: center; gap: var(--space-3); }
.field--switch span { margin: 0; }
.row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--space-4); align-items: end; }
.err { color: var(--color-danger); font-size: var(--text-sm); display: block; margin: var(--space-2) 0; }
.ok { color: var(--color-success, #2e7d32); font-size: var(--text-sm); }
.stock { display: flex; gap: var(--space-2); align-items: center; }
.stock :deep(input) { width: 90px; }
.variant-add { display: grid; grid-template-columns: 1fr 1fr 110px 110px auto; gap: var(--space-2); margin-top: var(--space-4); }
.gallery { display: flex; flex-wrap: wrap; gap: var(--space-4); }
.gallery__item { margin: 0; display: flex; flex-direction: column; gap: var(--space-1); }
.gallery__item img { width: 96px; height: 96px; object-fit: cover; border-radius: var(--radius-md); border: 1px solid var(--color-border); }
.gallery__add { display: grid; place-items: center; width: 96px; height: 96px; border: 1px dashed var(--color-border); border-radius: var(--radius-md); cursor: pointer; font-size: var(--text-xs); color: var(--color-text-muted); }
.gallery__add input { display: none; }
</style>
