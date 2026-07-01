<script setup lang="ts">
import { onMounted, ref } from "vue";
import { type AdminProduct, ApiError, api, formatPrice, name } from "../api";

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
    notice.value = e instanceof ApiError && e.status === 403 ? "You lack catalog access." : "Failed to load products.";
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
    notice.value = e instanceof ApiError && e.status === 403 ? "Your role can't create products." : "Create failed.";
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
    notice.value = e instanceof ApiError && e.status === 404 ? "Your role can't delete products." : "Delete failed.";
  }
}
onMounted(load);
</script>

<template>
  <section>
    <header class="page">
      <div>
        <h1>Products</h1>
        <p class="page__sub">Every catalog item, including those hidden from the storefront.</p>
      </div>
      <button class="btn btn--primary" @click="showForm = !showForm">
        {{ showForm ? "Close" : "New product" }}
      </button>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <form v-if="showForm" class="create" @submit.prevent="create">
      <input v-model="form.name" class="input create__name" placeholder="Product name" required />
      <input v-model.number="form.price_cents" class="input create__price" type="number" min="0" aria-label="price in cents" />
      <button class="btn btn--primary" :disabled="creating || !form.name">
        {{ creating ? "Adding…" : "Add" }}
      </button>
    </form>

    <div v-if="status === 'loading'" class="muted card card--pad">Loading…</div>
    <div v-else-if="status === 'ready'" class="card">
      <table class="tbl">
        <thead>
          <tr><th>Product</th><th>Status</th><th>Published</th><th>Storefront</th><th class="tbl__r"></th></tr>
        </thead>
        <tbody>
          <tr v-for="p in products" :key="p.id">
            <td>
              <span class="pname">{{ name(p) }}</span>
              <span class="pslug">/{{ p.slug }}</span>
            </td>
            <td><span :class="['badge', p.status === 'active' ? 'badge--ok' : 'badge--muted']">{{ p.status }}</span></td>
            <td class="muted">{{ p.published ? "Yes" : "No" }}</td>
            <td>
              <span :class="['badge', p.is_visible ? 'badge--ok' : 'badge--muted']">
                <span class="badge__dot" />{{ p.is_visible ? "Visible" : "Hidden" }}
              </span>
            </td>
            <td class="tbl__r"><button class="del" @click="remove(p)">Delete</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.page { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4); margin-bottom: var(--space-6); }
.page h1 { font-size: var(--text-2xl); }
.page__sub { color: var(--color-text-muted); margin: var(--space-1) 0 0; }
.notice { background: var(--color-danger-soft); color: var(--color-danger); padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); font-size: var(--text-sm); margin-bottom: var(--space-4); }
.create { display: flex; gap: var(--space-3); margin-bottom: var(--space-5); background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-4); box-shadow: var(--shadow-1); }
.create__name { flex: 1; }
.create__price { width: 8rem; }
.card { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); overflow: hidden; }
.card--pad { padding: var(--space-6); }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th { text-align: left; font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.04em; color: var(--color-text-faint); font-weight: var(--weight-semibold); padding: var(--space-3) var(--space-5); background: var(--color-surface); border-bottom: 1px solid var(--color-border); }
.tbl td { padding: var(--space-4) var(--space-5); border-bottom: 1px solid var(--color-surface); font-size: var(--text-sm); vertical-align: middle; }
.tbl tbody tr:last-child td { border-bottom: none; }
.tbl tbody tr:hover { background: var(--color-surface); }
.tbl__r { text-align: right; }
.pname { font-weight: var(--weight-medium); }
.pslug { color: var(--color-text-faint); margin-left: var(--space-2); }
.muted { color: var(--color-text-muted); }
.badge { text-transform: capitalize; }
.del { border: none; background: none; color: var(--color-danger); font: inherit; font-size: var(--text-sm); cursor: pointer; padding: 0; }
.del:hover { text-decoration: underline; }
</style>
