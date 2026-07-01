<script setup lang="ts">
import { onMounted, ref } from "vue";
import { type AdminProduct, ApiError, api, formatPrice, name } from "../api";

const products = ref<AdminProduct[]>([]);
const status = ref<"loading" | "error" | "ready">("loading");
const notice = ref<string | null>(null);

const form = ref({ category_id: 1, name: "", price_cents: 1999, description: "" });
const creating = ref(false);

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
    <h1>Products</h1>
    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <form class="create" @submit.prevent="create">
      <input v-model="form.name" placeholder="New product name" required />
      <input v-model.number="form.price_cents" type="number" min="0" aria-label="price in cents" />
      <button class="btn btn--primary" :disabled="creating || !form.name">
        {{ creating ? "Adding…" : "Add product" }}
      </button>
    </form>

    <div v-if="status === 'loading'" class="muted">Loading…</div>
    <table v-else-if="status === 'ready'" class="tbl">
      <thead>
        <tr><th>Name</th><th>Status</th><th>Published</th><th>Visible</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="p in products" :key="p.id">
          <td>{{ name(p) }}<span class="slug">/{{ p.slug }}</span></td>
          <td><span class="pill">{{ p.status }}</span></td>
          <td>{{ p.published ? "Yes" : "No" }}</td>
          <td>
            <span :class="['dot', p.is_visible ? 'dot--on' : 'dot--off']" />
            {{ p.is_visible ? "Visible" : "Hidden" }}
          </td>
          <td><button class="linkbtn linkbtn--danger" @click="remove(p)">Delete</button></td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
h1 { font-size: var(--text-2xl); margin-bottom: var(--space-4); }
.notice { color: var(--color-danger, #b00020); font-size: var(--text-sm); }
.create { display: flex; gap: var(--space-2); margin-bottom: var(--space-6); }
.create input { padding: var(--space-2) var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); font: inherit; }
.create input:first-child { flex: 1; }
.btn--primary { padding: var(--space-2) var(--space-4); border: none; border-radius: var(--radius-md); background: var(--color-accent); color: var(--color-text-inverse); cursor: pointer; font: inherit; }
.btn--primary:disabled { opacity: 0.5; }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th, .tbl td { text-align: left; padding: var(--space-3); border-bottom: 1px solid var(--color-border); font-size: var(--text-sm); }
.tbl th { color: var(--color-text-muted); font-weight: var(--weight-medium); }
.slug { color: var(--color-text-muted); margin-left: var(--space-2); }
.pill { padding: 2px var(--space-2); border: 1px solid var(--color-border); border-radius: var(--radius-full); font-size: var(--text-xs); }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.dot--on { background: var(--color-accent); }
.dot--off { background: var(--color-border); }
.linkbtn { border: none; background: none; cursor: pointer; font: inherit; color: var(--color-accent); }
.linkbtn--danger { color: var(--color-danger, #b00020); }
.muted { color: var(--color-text-muted); }
</style>
