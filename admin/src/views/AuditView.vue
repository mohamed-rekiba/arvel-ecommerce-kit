<script setup lang="ts">
import { onMounted, ref } from "vue";
import { type Activity, ApiError, api } from "../api";

const rows = ref<Activity[]>([]);
const status = ref<"loading" | "error" | "ready">("loading");
const notice = ref<string | null>(null);

async function load() {
  status.value = "loading";
  try {
    rows.value = await api.audit();
    status.value = "ready";
  } catch (e) {
    status.value = "error";
    notice.value =
      e instanceof ApiError && e.status === 403
        ? "You need the audit.view permission to see the audit log."
        : "Failed to load the audit log.";
  }
}

function when(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString() : "—";
}

onMounted(load);
</script>

<template>
  <section>
    <h1>Audit log</h1>
    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div v-if="status === 'loading'" class="muted">Loading…</div>
    <table v-else-if="status === 'ready'" class="tbl">
      <thead>
        <tr><th>When</th><th>Action</th><th>Subject</th><th>By (user)</th></tr>
      </thead>
      <tbody>
        <tr v-for="a in rows" :key="a.id">
          <td class="muted">{{ when(a.created_at) }}</td>
          <td>{{ a.description }}</td>
          <td class="muted">{{ a.subject_type ? `${a.subject_type} #${a.subject_id}` : "—" }}</td>
          <td class="muted">{{ a.causer_id ?? "—" }}</td>
        </tr>
        <tr v-if="rows.length === 0"><td colspan="4" class="muted">No activity yet.</td></tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
h1 { font-size: var(--text-2xl); margin-bottom: var(--space-4); }
.notice { color: var(--color-danger, #b00020); font-size: var(--text-sm); }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th, .tbl td { text-align: left; padding: var(--space-3); border-bottom: 1px solid var(--color-border); font-size: var(--text-sm); }
.tbl th { color: var(--color-text-muted); font-weight: var(--weight-medium); }
.muted { color: var(--color-text-muted); }
</style>
