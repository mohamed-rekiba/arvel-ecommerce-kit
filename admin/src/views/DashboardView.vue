<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { type Activity, type AdminProduct, api } from "../api";

const products = ref<AdminProduct[]>([]);
const total = ref(0);
const activity = ref<Activity[]>([]);
const canAudit = ref(true);
const loading = ref(true);

const visible = computed(() => products.value.filter((p) => p.is_visible).length);
const hidden = computed(() => products.value.filter((p) => !p.is_visible).length);
const drafts = computed(() => products.value.filter((p) => p.status === "draft").length);

const stats = computed(() => [
  { label: "Products", value: total.value, hint: "in the catalog" },
  { label: "Visible", value: visible.value, hint: "on the storefront", tone: "ok" as const },
  { label: "Hidden", value: hidden.value, hint: "unpublished / gated" },
  { label: "Drafts", value: drafts.value, hint: "not yet active" },
]);

function when(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";
}

onMounted(async () => {
  try {
    const page = await api.products();
    products.value = page.data;
    total.value = page.total;
  } catch {
    /* no catalog access — tiles stay at zero */
  }
  try {
    activity.value = await api.audit();
  } catch {
    canAudit.value = false;
  }
  loading.value = false;
});
</script>

<template>
  <section>
    <header class="page">
      <div>
        <h1>Overview</h1>
        <p class="page__sub">The back office at a glance.</p>
      </div>
      <RouterLink class="btn btn--primary" to="/products">Manage products</RouterLink>
    </header>

    <div class="stats">
      <article v-for="s in stats" :key="s.label" class="stat">
        <span class="stat__label">{{ s.label }}</span>
        <span class="stat__value">{{ loading ? "—" : s.value }}</span>
        <span class="stat__hint">
          <span v-if="s.tone === 'ok'" class="badge badge--ok"><span class="badge__dot" />live</span>
          {{ s.hint }}
        </span>
      </article>
    </div>

    <div class="card">
      <div class="card__head">
        <h2>Recent activity</h2>
        <RouterLink v-if="canAudit" class="card__link" to="/audit">View all</RouterLink>
      </div>
      <p v-if="!canAudit" class="empty">Your role can't view the audit log.</p>
      <p v-else-if="!loading && activity.length === 0" class="empty">No activity recorded yet.</p>
      <ul v-else class="feed">
        <li v-for="a in activity.slice(0, 6)" :key="a.id" class="feed__row">
          <span class="feed__dot" aria-hidden="true" />
          <span class="feed__desc">{{ a.description }}</span>
          <span class="feed__subject">{{ a.subject_type ? `${a.subject_type} #${a.subject_id}` : "" }}</span>
          <span class="feed__time">{{ when(a.created_at) }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.page { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4); margin-bottom: var(--space-8); }
.page h1 { font-size: var(--text-2xl); }
.page__sub { color: var(--color-text-muted); margin: var(--space-1) 0 0; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-4); margin-bottom: var(--space-8); }
@media (max-width: 860px) { .stats { grid-template-columns: repeat(2, 1fr); } }
.stat { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-5); box-shadow: var(--shadow-1); display: flex; flex-direction: column; gap: var(--space-2); }
.stat__label { font-size: var(--text-sm); color: var(--color-text-muted); font-weight: var(--weight-medium); }
.stat__value { font-size: var(--text-3xl); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); }
.stat__hint { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-xs); color: var(--color-text-faint); }
.card { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); }
.card__head { display: flex; align-items: center; justify-content: space-between; padding: var(--space-5) var(--space-6); border-bottom: 1px solid var(--color-border); }
.card__head h2 { font-size: var(--text-lg); }
.card__link { font-size: var(--text-sm); color: var(--color-accent); text-decoration: none; font-weight: var(--weight-medium); }
.empty { color: var(--color-text-muted); padding: var(--space-8) var(--space-6); text-align: center; margin: 0; }
.feed { list-style: none; margin: 0; padding: var(--space-2) 0; }
.feed__row { display: grid; grid-template-columns: auto 1fr auto auto; align-items: center; gap: var(--space-3); padding: var(--space-3) var(--space-6); }
.feed__row:not(:last-child) { border-bottom: 1px solid var(--color-surface); }
.feed__dot { width: 7px; height: 7px; border-radius: 50%; background: var(--color-accent); }
.feed__desc { font-weight: var(--weight-medium); }
.feed__subject { color: var(--color-text-muted); font-size: var(--text-sm); }
.feed__time { color: var(--color-text-faint); font-size: var(--text-xs); white-space: nowrap; }
</style>
