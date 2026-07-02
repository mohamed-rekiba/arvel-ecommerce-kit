<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { type Order, api, formatPrice, orderTokens } from "../api";

const route = useRoute();
const orderId = Number(route.params.id);
const token = orderTokens.get(orderId); // guests hold the receipt; signed-in owners use bearer

const order = ref<Order | null>(null);
const loading = ref(true);
const failed = ref(false);
const acting = ref(false);
const actionError = ref<string | null>(null);
let pollTimer: ReturnType<typeof setInterval> | null = null;

const cancellable = computed(
  () => order.value !== null && ["pending", "paid"].includes(order.value.status),
);
const payable = computed(() => order.value?.status === "pending");

function stopPolling() {
  if (pollTimer !== null) clearInterval(pollTimer);
  pollTimer = null;
}

async function load() {
  loading.value = true;
  failed.value = false;
  try {
    order.value = await api.order(orderId, token);
  } catch {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

async function payNow() {
  if (!order.value) return;
  acting.value = true;
  actionError.value = null;
  try {
    await api.pay(orderId, token);
    let attempts = 0;
    stopPolling();
    pollTimer = setInterval(async () => {
      attempts += 1;
      const fresh = await api.order(orderId, token);
      order.value = fresh;
      if (fresh.status === "paid" || fresh.payment_status === "failed" || attempts >= 20) {
        if (fresh.payment_status === "failed" && fresh.status !== "paid") {
          actionError.value = "The payment didn't go through. You can try again.";
        }
        acting.value = false;
        stopPolling();
      }
    }, 1000);
  } catch {
    acting.value = false;
    actionError.value = "We couldn't start the payment. Please try again.";
  }
}

async function cancelOrder() {
  if (!order.value) return;
  if (!window.confirm(`Cancel order #${orderId}? Items return to stock.`)) return;
  acting.value = true;
  actionError.value = null;
  try {
    order.value = await api.cancelOrder(orderId, token);
  } catch {
    actionError.value = "This order can no longer be cancelled.";
  } finally {
    acting.value = false;
  }
}

onMounted(load);
onBeforeUnmount(stopPolling);
</script>

<template>
  <main class="detail">
    <p v-if="loading" class="muted">Loading…</p>

    <div v-else-if="failed || !order" class="state">
      <h1>Order not found</h1>
      <p class="muted">We couldn't find that order — it may belong to another account.</p>
      <RouterLink class="btn btn--primary" to="/account">Back to your account</RouterLink>
    </div>

    <template v-else>
      <header class="detail__head">
        <p class="eyebrow">Your order</p>
        <h1>
          Order #{{ order.id }}
          <span class="badge" :class="`badge--${order.status}`">{{ order.status }}</span>
        </h1>
        <p v-if="order.payment_status === 'failed' && order.status === 'pending'" class="muted">
          Last payment attempt failed — you can try again below.
        </p>
      </header>

      <section class="panel">
        <h2>Items</h2>
        <ul class="lines">
          <li v-for="line in order.items" :key="line.product_variant_id">
            <span>{{ line.quantity }} × {{ line.product_name }} — {{ line.variant_name }}</span>
            <span>{{ formatPrice(line.unit_price_cents * line.quantity) }}</span>
          </li>
        </ul>
        <dl class="breakdown">
          <div><dt>Subtotal</dt><dd>{{ formatPrice(order.subtotal_cents) }}</dd></div>
          <div><dt>Shipping</dt><dd>{{ formatPrice(order.shipping_cents) }}</dd></div>
          <div><dt>Tax</dt><dd>{{ formatPrice(order.tax_cents) }}</dd></div>
          <div class="breakdown__total"><dt>Total</dt><dd>{{ formatPrice(order.total_cents) }}</dd></div>
        </dl>
      </section>

      <section class="panel">
        <h2>Delivery</h2>
        <address class="address">
          {{ order.address.name }}<br />
          {{ order.address.line1 }}<span v-if="order.address.line2"><br />{{ order.address.line2 }}</span><br />
          {{ order.address.city }}, {{ order.address.postal_code }} {{ order.address.country }}
        </address>
        <p class="muted">Updates go to {{ order.contact_email }}.</p>
      </section>

      <section class="actions" aria-live="polite">
        <p v-if="actionError" class="error" role="alert">{{ actionError }}</p>
        <button
          v-if="payable"
          class="btn btn--primary"
          :disabled="acting"
          @click="payNow"
        >
          {{ acting ? "Processing…" : `Pay ${formatPrice(order.total_cents)}` }}
        </button>
        <button v-if="cancellable" class="btn btn--danger" :disabled="acting" @click="cancelOrder">
          Cancel order
        </button>
        <p v-if="order.status === 'cancelled'" class="muted">
          This order was cancelled — the items are back in stock.
        </p>
      </section>
    </template>
  </main>
</template>

<style scoped>
.detail { max-width: 640px; margin: 0 auto; padding: var(--space-16) var(--container-pad) var(--space-16); }
.detail__head { margin-bottom: var(--space-8); }
.detail__head h1 { font-size: var(--text-3xl); margin-top: var(--space-2); display: flex; align-items: center; gap: var(--space-3); }
.badge { font-size: var(--text-xs); font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; padding: var(--space-1) var(--space-3); border-radius: var(--radius-full, 999px); background: var(--color-surface); border: 1px solid var(--color-border); }
.badge--paid { color: var(--color-success, #2e7d32); border-color: currentColor; }
.badge--cancelled { color: var(--color-danger); border-color: currentColor; }
.panel { background: var(--color-surface); border-radius: var(--radius-lg); padding: var(--space-6); margin-bottom: var(--space-5); }
.panel h2 { font-size: var(--text-sm); font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; color: var(--color-text-muted); margin: 0 0 var(--space-4); }
.lines { list-style: none; margin: 0; padding: 0; }
.lines li { display: flex; justify-content: space-between; gap: var(--space-4); padding: var(--space-3) 0; border-bottom: 1px solid var(--color-border); font-size: var(--text-sm); }
.breakdown { margin: var(--space-4) 0 0; }
.breakdown div { display: flex; justify-content: space-between; padding: var(--space-2) 0; font-size: var(--text-sm); }
.breakdown__total { border-top: 1px solid var(--color-border); font-weight: 600; font-size: var(--text-base); }
.breakdown dt { color: var(--color-text-muted); }
.breakdown dd { margin: 0; }
.address { font-style: normal; line-height: 1.6; margin-bottom: var(--space-3); }
.actions { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: center; }
.btn--danger { color: var(--color-danger); border-color: var(--color-danger); }
.error { width: 100%; color: var(--color-danger); font-size: var(--text-sm); }
.muted { color: var(--color-text-muted); font-size: var(--text-sm); }
.state { text-align: center; padding: var(--space-16) 0; }
</style>
