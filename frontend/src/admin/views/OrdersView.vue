<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Tag from "primevue/tag";
import { onMounted, ref } from "vue";
import { type Order, ApiError, ORDER_TRANSITIONS, api, formatPrice } from "../api";

const orders = ref<Order[]>([]);
const status = ref<"loading" | "error" | "ready">("loading");
const notice = ref<string | null>(null);
const busyId = ref<number | null>(null);

const severity: Record<string, string> = {
  pending: "secondary",
  paid: "info",
  shipped: "warn",
  delivered: "success",
  cancelled: "danger",
};

async function load() {
  status.value = "loading";
  try {
    orders.value = await api.orders();
    status.value = "ready";
  } catch (e) {
    status.value = "error";
    notice.value =
      e instanceof ApiError && e.status === 403 ? "You need the orders.view permission." : "Failed to load orders.";
  }
}

async function transition(order: Order, next: string) {
  busyId.value = order.id;
  notice.value = null;
  try {
    const updated = await api.updateOrderStatus(order.id, next);
    order.status = updated.status;
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? "Your role can't change order status." : "Transition failed.";
  } finally {
    busyId.value = null;
  }
}

function itemCount(o: Order): number {
  return o.items.reduce((n, i) => n + i.quantity, 0);
}
onMounted(load);
</script>

<template>
  <section class="page">
    <header class="head">
      <p class="eyebrow">Fulfillment</p>
      <h1>Orders</h1>
      <p class="sub">Every order, with state-machine transitions (order-manager or super-admin).</p>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="orders" :loading="status === 'loading'" paginator :rows="10" data-key="id" size="small" striped-rows>
        <template #empty><p class="empty">No orders yet.</p></template>
        <Column header="Order">
          <template #body="{ data }"><span class="mono">#{{ data.id }}</span></template>
        </Column>
        <Column header="Items">
          <template #body="{ data }">{{ itemCount(data) }}</template>
        </Column>
        <Column header="Total">
          <template #body="{ data }"><span class="mono">{{ formatPrice(data.total_cents) }}</span></template>
        </Column>
        <Column header="Status">
          <template #body="{ data }">
            <Tag :value="data.status" :severity="severity[data.status] ?? 'secondary'" />
          </template>
        </Column>
        <Column header="Advance">
          <template #body="{ data }">
            <div v-if="(ORDER_TRANSITIONS[data.status] ?? []).length" class="actions">
              <Button
                v-for="next in ORDER_TRANSITIONS[data.status]"
                :key="next"
                :label="next"
                size="small"
                :severity="next === 'cancelled' ? 'danger' : 'secondary'"
                outlined
                :loading="busyId === data.id"
                @click="transition(data, next)"
              />
            </div>
            <span v-else class="muted">—</span>
          </template>
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
.notice { background: var(--danger-bg); color: var(--danger-fg); padding: 10px 14px; border-radius: var(--radius-md); font-size: 13px; margin-bottom: 16px; }
.panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); overflow: hidden; }
.mono { font-family: var(--font-mono); font-size: 12.5px; }
.actions { display: inline-flex; gap: 6px; }
.muted { color: var(--text-subtle); }
.empty { text-align: center; color: var(--text-subtle); padding: 24px 0; }
</style>
