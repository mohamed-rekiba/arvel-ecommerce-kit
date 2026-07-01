<script setup lang="ts">
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Tag from "primevue/tag";
import { computed, onMounted, ref } from "vue";
import { type Activity, type AdminProduct, type Order, api, formatPrice } from "../api";

const products = ref<AdminProduct[]>([]);
const productTotal = ref(0);
const orders = ref<Order[]>([]);
const activity = ref<Activity[]>([]);
const canAudit = ref(true);
const loading = ref(true);

const visible = computed(() => products.value.filter((p) => p.is_visible).length);
const revenue = computed(() => orders.value.reduce((s, o) => s + o.total_cents, 0));
const pending = computed(() => orders.value.filter((o) => o.status === "pending" || o.status === "paid").length);

const stats = computed(() => [
  { label: "Revenue", value: formatPrice(revenue.value), icon: "pi-dollar", tone: "a" },
  { label: "Orders", value: String(orders.value.length), icon: "pi-shopping-bag", tone: "b" },
  { label: "Products", value: String(productTotal.value), icon: "pi-box", tone: "c" },
  { label: "Live on storefront", value: String(visible.value), icon: "pi-eye", tone: "d" },
]);

const severity: Record<string, string> = {
  pending: "secondary",
  paid: "info",
  shipped: "warn",
  delivered: "success",
  cancelled: "danger",
};

function when(iso: string | null): string {
  return iso
    ? new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
    : "—";
}

onMounted(async () => {
  try {
    const page = await api.products();
    products.value = page.data;
    productTotal.value = page.total;
  } catch {
    /* no catalog access */
  }
  try {
    orders.value = await api.orders();
  } catch {
    /* no orders access */
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
  <section class="dash">
    <header class="page">
      <div>
        <p class="eyebrow">Overview</p>
        <h1>Dashboard</h1>
        <p class="page__sub">Your store at a glance.</p>
      </div>
      <RouterLink class="cta" to="/admin/products"><i class="pi pi-box" /> Manage products</RouterLink>
    </header>

    <div class="kpis">
      <article v-for="s in stats" :key="s.label" class="kpi" :class="`kpi--${s.tone}`">
        <div class="kpi__row">
          <span class="kpi__label">{{ s.label }}</span>
          <span class="kpi__icn"><i :class="`pi ${s.icon}`" /></span>
        </div>
        <span class="kpi__val">{{ loading ? "—" : s.value }}</span>
        <span class="kpi__hint">{{ s.label === "Orders" && !loading ? `${pending} awaiting fulfillment` : " " }}</span>
      </article>
    </div>

    <div class="row2">
      <div class="panel">
        <div class="panel__head">
          <h2>Recent orders</h2>
          <RouterLink class="link" to="/admin/orders">View all →</RouterLink>
        </div>
        <DataTable :value="orders.slice(0, 8)" :loading="loading" size="small" data-key="id" class="tbl">
          <template #empty><p class="empty">No orders yet.</p></template>
          <Column header="Order">
            <template #body="{ data }"><span class="mono">#{{ data.id }}</span></template>
          </Column>
          <Column header="Items">
            <template #body="{ data }">{{ data.items.length }}</template>
          </Column>
          <Column header="Status">
            <template #body="{ data }">
              <Tag :value="data.status" :severity="severity[data.status] ?? 'secondary'" />
            </template>
          </Column>
          <Column header="Total" class="ta-r">
            <template #body="{ data }"><span class="mono">{{ formatPrice(data.total_cents) }}</span></template>
          </Column>
        </DataTable>
      </div>

      <div class="panel">
        <div class="panel__head">
          <h2>Recent activity</h2>
          <RouterLink v-if="canAudit" class="link" to="/admin/audit">View all →</RouterLink>
        </div>
        <p v-if="!canAudit" class="empty">Your role can't view the audit log.</p>
        <p v-else-if="!loading && !activity.length" class="empty">No activity recorded yet.</p>
        <ul v-else class="feed">
          <li v-for="a in activity.slice(0, 6)" :key="a.id" class="feed__row">
            <span class="feed__dot" />
            <span class="feed__desc">{{ a.description }}</span>
            <span class="feed__time">{{ when(a.created_at) }}</span>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: .16em; color: var(--accent); font-weight: 600; }
.page { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 24px; }
.page h1 { font-family: var(--font-display); font-size: 26px; font-weight: 700; letter-spacing: -.02em; margin: 6px 0 2px; }
.page__sub { color: var(--text-muted); font-size: 13px; margin: 0; }
.cta { display: inline-flex; align-items: center; gap: 8px; height: 40px; padding: 0 16px; border-radius: var(--radius-md); background: var(--accent); color: var(--on-accent); font-weight: 600; font-size: 14px; text-decoration: none; }

.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 22px; }
.kpi { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 18px; box-shadow: var(--shadow-1); }
.kpi__row { display: flex; align-items: center; justify-content: space-between; }
.kpi__label { font-size: 12.5px; color: var(--text-subtle); font-weight: 600; }
.kpi__icn { width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; font-size: 15px; }
.kpi--a .kpi__icn { background: var(--success-bg); color: var(--success-fg); }
.kpi--b .kpi__icn { background: var(--info-bg); color: var(--info-fg); }
.kpi--c .kpi__icn { background: color-mix(in srgb, var(--accent) 16%, transparent); color: var(--accent); }
.kpi--d .kpi__icn { background: var(--warn-bg); color: var(--warn-fg); }
.kpi__val { display: block; font-family: var(--font-display); font-weight: 800; font-size: 28px; margin-top: 10px; letter-spacing: -.02em; }
.kpi__hint { font-size: 11.5px; color: var(--text-subtle); }

.row2 { display: grid; grid-template-columns: 1.5fr 1fr; gap: 16px; }
.panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 18px; }
.panel__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.panel__head h2 { font-family: var(--font-display); font-size: 16px; font-weight: 700; }
.link { font-size: 12.5px; color: var(--accent); text-decoration: none; font-weight: 600; }
.empty { color: var(--text-subtle); text-align: center; padding: 28px 0; margin: 0; font-size: 14px; }
.mono { font-family: var(--font-mono); font-size: 12.5px; }
.tbl :deep(.ta-r) { text-align: right; }

.feed { list-style: none; margin: 0; padding: 4px 0; }
.feed__row { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 10px; padding: 9px 0; border-top: 1px solid var(--border); }
.feed__row:first-child { border-top: 0; }
.feed__dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); }
.feed__desc { font-size: 13px; }
.feed__time { color: var(--text-subtle); font-size: 11.5px; white-space: nowrap; }

@media (max-width: 900px) { .kpis { grid-template-columns: repeat(2, 1fr); } .row2 { grid-template-columns: 1fr; } }
</style>
