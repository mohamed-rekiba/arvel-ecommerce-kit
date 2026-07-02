<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Tag from "primevue/tag";
import ToggleSwitch from "primevue/toggleswitch";
import { computed, onMounted, reactive, ref } from "vue";
import { ApiError, api } from "../api";
import type { AdminCategory } from "../api";

const categories = ref<AdminCategory[]>([]);
const loading = ref(true);
const notice = ref<string | null>(null);
const dialogOpen = ref(false);
const editingId = ref<number | null>(null);
const saving = ref(false);

const form = reactive({
  en_name: "",
  fr_name: "",
  parent_id: null as number | null,
  published: true,
});

const parentOptions = computed(() => [
  { id: null, label: "— none —" },
  ...categories.value
    .filter((c) => c.id !== editingId.value)
    .map((c) => ({ id: c.id as number | null, label: catName(c) })),
]);

function catName(category: AdminCategory): string {
  return (
    category.translations.find((t) => t.locale === "en")?.name ?? category.slug
  );
}

function frName(category: AdminCategory): string | null {
  return category.translations.find((t) => t.locale === "fr")?.name ?? null;
}

async function load() {
  loading.value = true;
  try {
    categories.value = (await api.adminCategories()).data;
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? "You lack catalog access." : "Failed to load.";
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingId.value = null;
  Object.assign(form, { en_name: "", fr_name: "", parent_id: null, published: true });
  dialogOpen.value = true;
}

function openEdit(category: AdminCategory) {
  editingId.value = category.id;
  Object.assign(form, {
    en_name: catName(category),
    fr_name: frName(category) ?? "",
    parent_id: category.parent_id,
    published: category.published,
  });
  dialogOpen.value = true;
}

function translationsPayload() {
  const payload: Record<string, { name: string }> = { en: { name: form.en_name } };
  if (form.fr_name.trim()) payload.fr = { name: form.fr_name };
  return payload;
}

async function save() {
  saving.value = true;
  notice.value = null;
  try {
    if (editingId.value === null) {
      await api.createCategory({
        translations: translationsPayload(),
        parent_id: form.parent_id,
        published: form.published,
      });
    } else {
      await api.updateCategory(editingId.value, {
        translations: translationsPayload(),
        parent_id: form.parent_id ?? undefined,
        published: form.published,
      });
    }
    dialogOpen.value = false;
    await load();
  } catch (e) {
    notice.value =
      e instanceof ApiError
        ? Object.values(e.errors)[0]?.[0] ?? "Save failed."
        : "Save failed.";
  } finally {
    saving.value = false;
  }
}

async function remove(category: AdminCategory) {
  if (!window.confirm(`Delete category “${catName(category)}”?`)) return;
  notice.value = null;
  try {
    await api.deleteCategory(category.id);
    await load();
  } catch (e) {
    notice.value =
      e instanceof ApiError
        ? Object.values(e.errors)[0]?.[0] ?? "Delete failed."
        : "Delete failed.";
  }
}

onMounted(load);
</script>

<template>
  <section class="page">
    <header class="head">
      <div>
        <p class="eyebrow">Catalog</p>
        <h1>Categories</h1>
        <p class="sub">Per-locale names; visibility flows into the retrievable views.</p>
      </div>
      <Button label="New category" icon="pi pi-plus" @click="openCreate" />
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="categories" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty><p class="empty">No categories.</p></template>
        <Column header="Category">
          <template #body="{ data }">
            <div class="pname">{{ catName(data) }}</div>
            <div class="pslug">/{{ data.slug }} <span v-if="frName(data)">· fr: {{ frName(data) }}</span></div>
          </template>
        </Column>
        <Column header="Parent">
          <template #body="{ data }">
            {{ data.parent_id ? catName(categories.find((c) => c.id === data.parent_id) ?? data) : "—" }}
          </template>
        </Column>
        <Column header="Published">
          <template #body="{ data }">
            <Tag :value="data.published ? 'Published' : 'Hidden'" :severity="data.published ? 'success' : 'secondary'" />
          </template>
        </Column>
        <Column header="Storefront">
          <template #body="{ data }">
            <Tag :value="data.is_visible ? 'Visible' : 'Hidden'" :severity="data.is_visible ? 'success' : 'secondary'" />
          </template>
        </Column>
        <Column header="" style="width: 8rem">
          <template #body="{ data }">
            <Button icon="pi pi-pencil" text rounded aria-label="Edit" @click="openEdit(data)" />
            <Button icon="pi pi-trash" text rounded severity="danger" aria-label="Delete" @click="remove(data)" />
          </template>
        </Column>
      </DataTable>
    </div>

    <Dialog v-model:visible="dialogOpen" modal :header="editingId === null ? 'New category' : 'Edit category'" :style="{ width: '26rem' }">
      <form class="form" @submit.prevent="save">
        <label class="field"><span>Name (en)</span><InputText v-model="form.en_name" required /></label>
        <label class="field"><span>Name (fr)</span><InputText v-model="form.fr_name" /></label>
        <label class="field"><span>Parent</span>
          <Select v-model="form.parent_id" :options="parentOptions" optionLabel="label" optionValue="id" />
        </label>
        <label class="field field--switch"><span>Published</span><ToggleSwitch v-model="form.published" /></label>
        <Button type="submit" :label="saving ? 'Saving…' : 'Save'" :disabled="saving || !form.en_name" />
      </form>
    </Dialog>
  </section>
</template>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: start; margin-bottom: var(--space-6); }
.pname { font-weight: 600; }
.pslug { font-size: var(--text-xs); color: var(--color-text-muted); }
.panel { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); }
.notice { color: var(--color-danger); margin-bottom: var(--space-4); }
.form .field { display: block; margin-bottom: var(--space-4); }
.field span { display: block; font-size: var(--text-sm); margin-bottom: var(--space-1); }
.field :deep(input) { width: 100%; }
.field--switch { display: flex; align-items: center; gap: var(--space-3); }
.field--switch span { margin: 0; }
.empty { padding: var(--space-4); color: var(--color-text-muted); }
</style>
