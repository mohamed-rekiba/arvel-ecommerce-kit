<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import InputText from "primevue/inputtext";
import Tag from "primevue/tag";
import ToggleSwitch from "primevue/toggleswitch";
import { onMounted, ref } from "vue";
import { ApiError, type Vendor, api } from "../api";
import { t } from "../locale";

const vendors = ref<Vendor[]>([]);
const loading = ref(true);
const notice = ref<string | null>(null);
const newName = ref("");
const creating = ref(false);

async function load() {
  loading.value = true;
  try {
    vendors.value = await api.vendors();
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t("common.no_catalog") : t("common.load_error");
  } finally {
    loading.value = false;
  }
}

async function create() {
  creating.value = true;
  notice.value = null;
  try {
    await api.createVendor({ name: newName.value });
    newName.value = "";
    await load();
  } catch (e) {
    notice.value =
      e instanceof ApiError ? Object.values(e.errors)[0]?.[0] ?? t("vendors.create_error") : t("vendors.create_error");
  } finally {
    creating.value = false;
  }
}

async function togglePublished(vendor: Vendor) {
  notice.value = null;
  try {
    const updated = await api.updateVendor(vendor.id, { published: !vendor.published });
    vendors.value = vendors.value.map((v) => (v.id === updated.id ? updated : v));
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t("vendors.no_update") : t("vendors.update_error");
    await load();
  }
}

onMounted(load);
</script>

<template>
  <section class="page">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t("nav.catalog") }}</p>
        <h1>{{ t("nav.vendors") }}</h1>
        <p class="sub">{{ t("vendors.sub") }}</p>
      </div>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <form class="create" @submit.prevent="create">
      <InputText v-model="newName" :placeholder="t('vendors.name')" class="grow" />
      <Button type="submit" :label="creating ? t('vendors.adding') : t('vendors.add')" :disabled="creating || !newName" />
    </form>

    <div class="panel">
      <DataTable :value="vendors" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty><p class="empty">{{ t("vendors.none") }}</p></template>
        <Column field="name" :header="t('vendors.vendor')" />
        <Column field="slug" :header="t('vendors.slug')">
          <template #body="{ data }"><span class="pslug">/{{ data.slug }}</span></template>
        </Column>
        <Column :header="t('common.status')">
          <template #body="{ data }">
            <Tag :value="data.published ? t('categories.published') : t('vendors.unpublished')" :severity="data.published ? 'success' : 'warn'" />
          </template>
        </Column>
        <Column :header="t('categories.published')" style="width: 7rem">
          <template #body="{ data }">
            <ToggleSwitch :modelValue="data.published" @update:modelValue="togglePublished(data)" :aria-label="t('vendors.toggle', { name: data.name })" />
          </template>
        </Column>
      </DataTable>
    </div>
  </section>
</template>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: start; margin-bottom: var(--space-6); }
.create { display: flex; gap: var(--space-2); margin-bottom: var(--space-4); }
.create .grow { flex: 1; }
.panel { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); }
.notice { color: var(--color-danger); margin-bottom: var(--space-4); }
.pslug { font-size: var(--text-xs); color: var(--color-text-muted); }
.empty { padding: var(--space-4); color: var(--color-text-muted); }
</style>
