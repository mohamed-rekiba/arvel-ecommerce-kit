<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Tag from "primevue/tag";
import { onMounted, ref } from "vue";
import { type Order, type OrderStatus, ApiError, ORDER_TRANSITIONS, api, formatPrice } from "../api";
import { type MessageKey, t } from "../locale";

const orders = ref<Order[]>([]);
const status = ref<"loading" | "error" | "ready">("loading");
const notice = ref<string | null>(null);
const busyId = ref<number | null>(null);

function nextStates(status: OrderStatus): OrderStatus[] {
  return ORDER_TRANSITIONS[status] ?? [];
}

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
      e instanceof ApiError && e.status === 403 ? t("orders.no_view") : t("orders.load_error");
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
      e instanceof ApiError && e.status === 403 ? t("orders.no_transition") : t("orders.transition_error");
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
      <p class="eyebrow">{{ t("orders.eyebrow") }}</p>
      <h1>{{ t("nav.orders") }}</h1>
      <p class="sub">{{ t("orders.sub") }}</p>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="orders" :loading="status === 'loading'" paginator :rows="10" data-key="id" size="small" striped-rows>
        <template #empty><p class="empty">{{ t("orders.none") }}</p></template>
        <Column :header="t('orders.order')">
          <template #body="{ data }">
            <RouterLink class="olink mono" :to="`/admin/orders/${data.id}`">#{{ data.id }}</RouterLink>
          </template>
        </Column>
        <Column :header="t('orders.items')">
          <template #body="{ data }">{{ itemCount(data) }}</template>
        </Column>
        <Column :header="t('common.total')">
          <template #body="{ data }"><span class="mono">{{ formatPrice(data.total_cents) }}</span></template>
        </Column>
        <Column :header="t('common.status')">
          <template #body="{ data }">
            <Tag :value="t(`order.${data.status}` as MessageKey)" :severity="severity[data.status] ?? 'secondary'" />
          </template>
        </Column>
        <Column :header="t('orders.advance')">
          <template #body="{ data }">
            <div v-if="nextStates(data.status).length" class="actions">
              <Button
                v-for="next in nextStates(data.status)"
                :key="next"
                :label="t(`order.${next}` as MessageKey)"
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
.olink { color: inherit; }
.olink:hover { text-decoration: underline; }
</style>
