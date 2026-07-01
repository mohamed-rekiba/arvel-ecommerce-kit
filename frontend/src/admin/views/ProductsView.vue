<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Tag from "primevue/tag";
import { onMounted, ref } from "vue";
import { type AdminProduct, ApiError, api, name } from "../api";

const products = ref<AdminProduct[]>([]);
const status = ref<"loading" | "error" | "ready">("loading");
const notice = ref<string | null>(null);

const form = ref({ category_id: 1, name: "", price_cents: 1999, description: "" });
const creating = ref(false);
const showForm = ref(false);

async function load() {
  status.value = "loading";
  try {
    products.value = (await api.products()).data;
    status.value = "ready";
  } catch (e) {
    status.value = "error";
    notice.value =
      e instanceof ApiError && e.status === 403 ? "You lack catalog access." : "Failed to load products.";
  }
}

async function create() {
  creating.value = true;
  notice.value = null;
  try {
    await api.createProduct({ ...form.value });
    form.value.name = "";
    showForm.value = false;
    await load();
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? "Your role can't create products." : "Create failed.";
  } finally {
    creating.value = false;
  }
}

async function remove(p: AdminProduct) {
  notice.value = null;
  try {
    await api.deleteProduct(p.id);
    await load();
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 404 ? "Your role can't delete products." : "Delete failed.";
  }
}
onMounted(load);
</script>

<template>
  <section class="page">
    <header class="head">
      <div>
        <p class="eyebrow">Catalog</p>
        <h1>Products</h1>
        <p class="sub">Every catalog item, including those hidden from the storefront.</p>
      </div>
      <Button
        :label="showForm ? 'Close' : 'New product'"
        :icon="showForm ? 'pi pi-times' : 'pi pi-plus'"
        @click="showForm = !showForm"
      />
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <form v-if="showForm" class="create" @submit.prevent="create">
      <InputText v-model="form.name" placeholder="Product name" class="grow" />
      <InputNumber v-model="form.price_cents" :min="0" placeholder="Price (cents)" />
      <Button type="submit" :label="creating ? 'Adding…' : 'Add'" :loading="creating" :disabled="!form.name" />
    </form>

    <div class="panel">
      <DataTable
        :value="products"
        :loading="status === 'loading'"
        paginator
        :rows="10"
        data-key="id"
        size="small"
        striped-rows
      >
        <template #empty><p class="empty">No products.</p></template>
        <Column header="Product">
          <template #body="{ data }">
            <div class="pname">{{ name(data) }}</div>
            <div class="pslug">/{{ data.slug }}</div>
          </template>
        </Column>
        <Column header="Status">
          <template #body="{ data }">
            <Tag :value="data.status" :severity="data.status === 'active' ? 'success' : 'secondary'" />
          </template>
        </Column>
        <Column header="Storefront">
          <template #body="{ data }">
            <Tag
              :value="data.is_visible ? 'Visible' : 'Hidden'"
              :severity="data.is_visible ? 'success' : 'secondary'"
            />
          </template>
        </Column>
        <Column header="" style="width: 5rem">
          <template #body="{ data }">
            <Button icon="pi pi-trash" text rounded severity="danger" aria-label="Delete" @click="remove(data)" />
          </template>
        </Column>
      </DataTable>
    </div>
  </section>
</template>

<style scoped>
.eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: .16em; color: var(--accent); font-weight: 600; }
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 20px; }
.head h1 { font-family: var(--font-display); font-size: 26px; font-weight: 700; letter-spacing: -.02em; margin: 6px 0 2px; }
.sub { color: var(--text-muted); font-size: 13px; margin: 0; }
.notice { background: var(--danger-bg); color: var(--danger-fg); padding: 10px 14px; border-radius: var(--radius-md); font-size: 13px; margin-bottom: 16px; }
.create { display: flex; gap: 10px; margin-bottom: 18px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 14px; box-shadow: var(--shadow-1); }
.create .grow { flex: 1; }
.panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); overflow: hidden; }
.pname { font-weight: 600; font-size: 13.5px; }
.pslug { color: var(--text-subtle); font-size: 11.5px; }
.empty { text-align: center; color: var(--text-subtle); padding: 24px 0; }
</style>
