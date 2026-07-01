<script setup lang="ts">
import Column from "primevue/column";
import DataTable from "primevue/datatable";
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
  <section class="page">
    <header class="head">
      <p class="eyebrow">System</p>
      <h1>Audit log</h1>
      <p class="sub">Every back-office action — who did what, to which record.</p>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div v-else class="panel">
      <DataTable :value="rows" :loading="status === 'loading'" paginator :rows="15" data-key="id" size="small" striped-rows>
        <template #empty><p class="empty">No activity recorded yet.</p></template>
        <Column header="When">
          <template #body="{ data }"><span class="muted nowrap">{{ when(data.created_at) }}</span></template>
        </Column>
        <Column header="Action">
          <template #body="{ data }"><span class="dot" />{{ data.description }}</template>
        </Column>
        <Column header="Subject">
          <template #body="{ data }"><span class="muted">{{ data.subject_type ? `${data.subject_type} #${data.subject_id}` : "—" }}</span></template>
        </Column>
        <Column header="User">
          <template #body="{ data }"><span class="muted">{{ data.causer_id != null ? `#${data.causer_id}` : "—" }}</span></template>
        </Column>
      </DataTable>
    </div>
  </section>
</template>

<style scoped>
.eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: .16em; color: var(--accent); font-weight: 600; }
.head { margin-bottom: 20px; }
.head h1 { font-family: var(--font-display); font-size: 26px; font-weight: 700; letter-spacing: -.02em; margin: 6px 0 2px; }
.sub { color: var(--text-muted); font-size: 13px; margin: 0; }
.notice { background: var(--danger-bg); color: var(--danger-fg); padding: 10px 14px; border-radius: var(--radius-md); font-size: 13px; }
.panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); overflow: hidden; }
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--accent); margin-right: 8px; }
.muted { color: var(--text-muted); }
.nowrap { white-space: nowrap; }
.empty { text-align: center; color: var(--text-subtle); padding: 24px 0; }
</style>
