<script setup lang="ts">
import { onMounted, ref } from "vue";
import { type Order, ApiError, ORDER_TRANSITIONS, api, formatPrice } from "../api";

const orders = ref<Order[]>([]);
const status = ref<"loading" | "error" | "ready">("loading");
const notice = ref<string | null>(null);
const busyId = ref<number | null>(null);

const badgeClass: Record<string, string> = {
  pending: "badge--warn",
  paid: "badge--ok",
  shipped: "badge--ok",
  delivered: "badge--ok",
  cancelled: "badge--muted",
};

async function load() {
  status.value = "loading";
  try {
    orders.value = await api.orders();
    status.value = "ready";
  } catch (e) {
    status.value = "error";
    notice.value = e instanceof ApiError && e.status === 403 ? "You need the orders.view permission." : "Failed to load orders.";
  }
}

async function transition(order: Order, next: string) {
  busyId.value = order.id;
  notice.value = null;
  try {
    const updated = await api.updateOrderStatus(order.id, next);
    order.status = updated.status;
  } catch (e) {
    notice.value = e instanceof ApiError && e.status === 403 ? "Your role can't change order status." : "Transition failed.";
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
  <section>
    <header class="page">
      <h1>Orders</h1>
      <p class="page__sub">Every order, with state-machine transitions (order-manager or super-admin).</p>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div v-if="status === 'loading'" class="muted">Loading…</div>
    <div v-else-if="status === 'ready' && orders.length === 0" class="card card--pad muted">No orders yet.</div>
    <div v-else-if="status === 'ready'" class="card">
      <table class="tbl">
        <thead>
          <tr><th>Order</th><th>Items</th><th>Total</th><th>Status</th><th class="tbl__r">Advance</th></tr>
        </thead>
        <tbody>
          <tr v-for="o in orders" :key="o.id">
            <td class="mono">#{{ o.id }}</td>
            <td class="muted">{{ itemCount(o) }} item{{ itemCount(o) === 1 ? "" : "s" }}</td>
            <td>{{ formatPrice(o.total_cents) }}</td>
            <td><span :class="['badge', badgeClass[o.status] ?? 'badge--muted']"><span class="badge__dot" />{{ o.status }}</span></td>
            <td class="tbl__r">
              <div v-if="(ORDER_TRANSITIONS[o.status] ?? []).length" class="actions">
                <button
                  v-for="next in ORDER_TRANSITIONS[o.status]"
                  :key="next"
                  class="btn btn--sm"
                  :disabled="busyId === o.id"
                  @click="transition(o, next)"
                >
                  {{ next }}
                </button>
              </div>
              <span v-else class="muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.page { margin-bottom: var(--space-6); }
.page h1 { font-size: var(--text-2xl); }
.page__sub { color: var(--color-text-muted); margin: var(--space-1) 0 0; }
.notice { background: var(--color-danger-soft); color: var(--color-danger); padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); font-size: var(--text-sm); margin-bottom: var(--space-4); }
.card { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); overflow: hidden; }
.card--pad { padding: var(--space-6); }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th { text-align: left; font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.04em; color: var(--color-text-faint); font-weight: var(--weight-semibold); padding: var(--space-3) var(--space-5); background: var(--color-surface); border-bottom: 1px solid var(--color-border); }
.tbl td { padding: var(--space-4) var(--space-5); border-bottom: 1px solid var(--color-surface); font-size: var(--text-sm); vertical-align: middle; }
.tbl tbody tr:last-child td { border-bottom: none; }
.tbl tbody tr:hover { background: var(--color-surface); }
.tbl__r { text-align: right; }
.mono { font-family: ui-monospace, monospace; font-weight: var(--weight-medium); }
.badge { text-transform: capitalize; }
.actions { display: inline-flex; gap: var(--space-2); justify-content: flex-end; }
.btn--sm { padding: 3px var(--space-3); font-size: var(--text-xs); text-transform: capitalize; }
.muted { color: var(--color-text-muted); }
</style>
