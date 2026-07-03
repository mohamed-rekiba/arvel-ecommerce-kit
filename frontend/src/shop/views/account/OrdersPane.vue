<script setup lang="ts">
// My Orders (profile ref 5): order cards — header band (id · placed date · total · payment
// method) + status chip, product thumbs, and per-order actions: Track / Invoice / Cancel /
// Add review. Invoice opens the server-rendered print view in a new tab (receipt token in
// the URL — a browser tab can't send bearer headers).
import { onMounted, ref } from "vue";
import { type Order, api, formatPrice } from "../../api";
import { type MessageKey, t } from "../../locale";

const orders = ref<Order[]>([]);
const loading = ref(true);
const cancelMsg = ref<string | null>(null);

async function load() {
  loading.value = true;
  try {
    orders.value = await api.myOrders();
  } catch {
    orders.value = [];
  } finally {
    loading.value = false;
  }
}

function placedAt(order: Order): string {
  return order.placed_at ? new Date(order.placed_at).toLocaleDateString() : "—";
}

const cancellable = (o: Order) => o.status === "pending" || o.status === "paid";

async function cancel(order: Order) {
  if (!window.confirm(t("order.cancel_confirm", { n: order.id }))) return;
  cancelMsg.value = null;
  try {
    await api.cancelOrder(order.id, order.token);
    cancelMsg.value = t("account.order_cancelled_ok");
    await load();
  } catch {
    cancelMsg.value = t("order.cancel_error");
  }
}

function openInvoice(order: Order) {
  window.open(api.invoiceUrl(order.id, order.token), "_blank", "noopener");
}

onMounted(load);
</script>

<template>
  <div class="card">
    <h2 class="card__title">{{ t("account.menu_orders") }}</h2>
    <p v-if="cancelMsg" class="notice" role="status">{{ cancelMsg }}</p>
    <p v-if="loading" class="muted">{{ t("common.loading") }}</p>
    <p v-else-if="!orders.length" class="muted">{{ t("account.no_orders") }}</p>

    <ul v-else class="list">
      <li v-for="o in orders" :key="o.id" class="order">
        <div class="order__head">
          <div class="order__facts">
            <span class="fact"><i>{{ t("checkout.order") }}</i><b>#{{ o.id }}</b></span>
            <span class="fact"><i>{{ t("account.order_placed") }}</i><b>{{ placedAt(o) }}</b></span>
            <span class="fact"><i>{{ t("account.order_method") }}</i><b>{{ t(`pay.${o.payment_method}` as MessageKey) }}</b></span>
            <span class="fact"><i>{{ t("cart.total") }}</i><b class="tnum">{{ formatPrice(o.total_cents) }}</b></span>
          </div>
          <span class="chip" :class="`chip--${o.status}`">{{ t(`order.${o.status}` as MessageKey) }}</span>
        </div>

        <div class="order__body">
          <ul class="thumbs">
            <li v-for="line in o.items.slice(0, 4)" :key="line.product_variant_id" class="thumb">
              <img v-if="line.image_url" :src="line.image_url" :alt="line.product_name" />
              <span v-else class="thumb__ph" aria-hidden="true" />
              <i v-if="line.quantity > 1" class="thumb__n">×{{ line.quantity }}</i>
            </li>
            <li v-if="o.items.length > 4" class="thumb thumb--more">+{{ o.items.length - 4 }}</li>
          </ul>
          <div class="order__actions">
            <RouterLink class="act act--primary" :to="`/orders/${o.id}`">{{ t("account.order_track") }}</RouterLink>
            <button class="act" @click="openInvoice(o)">{{ t("account.order_invoice") }}</button>
            <RouterLink
              v-if="o.status === 'delivered' && o.items[0]"
              class="act"
              :to="`/orders/${o.id}`"
            >{{ t("account.order_review") }}</RouterLink>
            <button v-if="cancellable(o)" class="act act--danger" @click="cancel(o)">{{ t("order.cancel") }}</button>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: clamp(1rem, 3vw, 1.75rem); }
.card__title { font-family: var(--font-display); font-size: 1.15rem; font-weight: 800; margin-bottom: 18px; }
.muted { color: var(--text-subtle); }
.notice { background: var(--info-bg); color: var(--info-fg); border-radius: var(--radius-sm); padding: 9px 13px; font-size: 13px; margin-bottom: 14px; }

.list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 14px; }
.order { border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; }
.order__head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; padding: 12px 14px; background: var(--band); border-bottom: 1px solid var(--border); }
.order__facts { display: flex; flex-wrap: wrap; gap: 14px 22px; }
.fact { display: flex; flex-direction: column; }
.fact i { font-style: normal; font-size: 10.5px; letter-spacing: .05em; text-transform: uppercase; color: var(--text-subtle); }
.fact b { font-size: 13px; font-weight: 700; }
.chip { padding: 4px 12px; border-radius: var(--radius-full); font-size: 11.5px; font-weight: 700; text-transform: capitalize; background: var(--info-bg); color: var(--info-fg); }
.chip--paid, .chip--delivered { background: var(--success-bg); color: var(--success-fg); }
.chip--cancelled { background: var(--danger-bg); color: var(--danger-fg); }
.chip--shipped { background: var(--warn-bg); color: var(--warn-fg); }

.order__body { display: flex; flex-direction: column; gap: 12px; padding: 12px 14px; }
.thumbs { list-style: none; margin: 0; padding: 0; display: flex; gap: 8px; }
.thumb { position: relative; width: 52px; height: 52px; border-radius: var(--radius-sm); overflow: hidden; background: var(--photo-well); border: 1px solid var(--border); display: grid; place-items: center; }
.thumb img { width: 100%; height: 100%; object-fit: cover; }
[data-theme="dark"] .thumb img { filter: brightness(.88); }
.thumb__ph { width: 100%; height: 100%; background: var(--surface-2); }
.thumb__n { position: absolute; bottom: 1px; inset-inline-end: 2px; font-style: normal; font-size: 10px; font-weight: 800; background: color-mix(in srgb, var(--nav-bg) 82%, transparent); color: var(--nav-text-hi); padding: 0 4px; border-radius: 4px; }
.thumb--more { font-size: 12px; font-weight: 700; color: var(--text-muted); }

.order__actions { display: flex; flex-wrap: wrap; gap: 8px; }
.act { padding: 8px 15px; border-radius: var(--radius-full); border: 1px solid var(--border-2); background: var(--surface); color: var(--text); font-size: 12.5px; font-weight: 600; text-decoration: none; cursor: pointer; }
.act:hover { border-color: var(--accent); color: var(--accent-text); }
.act--primary { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
.act--primary:hover { color: var(--on-accent); opacity: .92; }
.act--danger { color: var(--sale); border-color: color-mix(in srgb, var(--sale) 40%, var(--border-2)); }
.act--danger:hover { border-color: var(--sale); color: var(--sale); }

@media (min-width: 640px) {
  .order__body { flex-direction: row; align-items: center; justify-content: space-between; }
}
</style>
