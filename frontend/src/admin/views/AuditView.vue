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
    <header class="page">
      <h1>Audit log</h1>
      <p class="page__sub">Every back-office action — who did what, to which record.</p>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div v-if="status === 'loading'" class="muted">Loading…</div>
    <div v-else-if="status === 'ready'" class="card">
      <table class="tbl">
        <thead>
          <tr><th>When</th><th>Action</th><th>Subject</th><th>User</th></tr>
        </thead>
        <tbody>
          <tr v-for="a in rows" :key="a.id">
            <td class="muted nowrap">{{ when(a.created_at) }}</td>
            <td><span class="dot" aria-hidden="true" />{{ a.description }}</td>
            <td class="muted">{{ a.subject_type ? `${a.subject_type} #${a.subject_id}` : "—" }}</td>
            <td class="muted">{{ a.causer_id != null ? `#${a.causer_id}` : "—" }}</td>
          </tr>
          <tr v-if="rows.length === 0"><td colspan="4" class="empty">No activity recorded yet.</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.page { margin-bottom: var(--space-6); }
.page h1 { font-size: var(--text-2xl); }
.page__sub { color: var(--color-text-muted); margin: var(--space-1) 0 0; }
.notice { background: var(--color-danger-soft); color: var(--color-danger); padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); font-size: var(--text-sm); }
.card { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); overflow: hidden; }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th { text-align: left; font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.04em; color: var(--color-text-faint); font-weight: var(--weight-semibold); padding: var(--space-3) var(--space-5); background: var(--color-surface); border-bottom: 1px solid var(--color-border); }
.tbl td { padding: var(--space-4) var(--space-5); border-bottom: 1px solid var(--color-surface); font-size: var(--text-sm); }
.tbl tbody tr:last-child td { border-bottom: none; }
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--color-accent); margin-right: var(--space-2); }
.muted { color: var(--color-text-muted); }
.nowrap { white-space: nowrap; }
.empty { text-align: center; color: var(--color-text-muted); padding: var(--space-8); }
</style>
