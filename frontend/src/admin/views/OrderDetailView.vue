<script setup lang="ts">
import Button from "primevue/button";
import Tag from "primevue/tag";
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import {
  ApiError,
  ORDER_TRANSITIONS,
  type AdminOrderDetail,
  type OrderStatus,
  api,
  formatPrice,
} from "../api";

const route = useRoute();
const orderId = Number(route.params.id);
const order = ref<AdminOrderDetail | null>(null);
const loading = ref(true);
const notice = ref<string | null>(null);
const acting = ref(false);

const nextStates = computed<OrderStatus[]>(() =>
  order.value ? (ORDER_TRANSITIONS[order.value.status] ?? []) : [],
);

async function load() {
  loading.value = true;
  try {
    order.value = await api.adminOrder(orderId);
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? "You may not view orders." : "Couldn't load.";
  } finally {
    loading.value = false;
  }
}

async function advance(next: OrderStatus) {
  acting.value = true;
  notice.value = null;
  try {
    await api.updateOrderStatus(orderId, next);
    await load();
  } catch (e) {
    notice.value =
      e instanceof ApiError
        ? Object.values(e.errors)[0]?.[0] ?? "That transition isn't allowed."
        : "Transition failed.";
  } finally {
    acting.value = false;
  }
}

const formatWhen = (iso: string | null) => (iso ? new Date(iso).toLocaleString() : "");

const severity = (status: string) =>
  status === "paid" || status === "delivered"
    ? "success"
    : status === "cancelled"
      ? "danger"
      : "secondary";

onMounted(load);
</script>

<template>
  <section class="page">
    <p v-if="loading">Loading…</p>
    <p v-else-if="!order" class="notice" role="alert">{{ notice }}</p>

    <template v-else>
      <header class="head">
        <div>
          <RouterLink class="back" to="/admin/orders">← Orders</RouterLink>
          <h1>
            Order #{{ order.id }}
            <Tag :value="order.status" :severity="severity(order.status)" />
          </h1>
          <p class="sub">
            <template v-if="order.customer">
              <RouterLink :to="`/admin/users`">{{ order.customer.name }}</RouterLink>
              · {{ order.customer.email }}
            </template>
            <template v-else>Guest order · {{ order.contact_email }}</template>
          </p>
        </div>
        <div class="actions">
          <Button
            v-for="next in nextStates"
            :key="next"
            :label="next"
            :severity="next === 'cancelled' ? 'danger' : 'secondary'"
            outlined
            size="small"
            :disabled="acting"
            @click="advance(next)"
          />
        </div>
      </header>

      <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

      <div class="grid">
        <section class="card">
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
            <div v-if="order.discount_cents > 0" class="breakdown__discount">
              <dt>Discount{{ order.coupon_code ? ` (${order.coupon_code})` : "" }}</dt>
              <dd>−{{ formatPrice(order.discount_cents) }}</dd>
            </div>
            <div class="breakdown__total"><dt>Total</dt><dd>{{ formatPrice(order.total_cents) }}</dd></div>
          </dl>
        </section>

        <section class="card">
          <h2>Delivery</h2>
          <address class="address">
            {{ order.address.name }}<br />
            {{ order.address.line1 }}<span v-if="order.address.line2"><br />{{ order.address.line2 }}</span><br />
            {{ order.address.city }}, {{ order.address.postal_code }} {{ order.address.country }}
          </address>

          <h2>Payments</h2>
          <p v-if="order.payments.length === 0" class="muted">No payment attempts.</p>
          <ul class="lines">
            <li v-for="p in order.payments" :key="p.id">
              <span><code>{{ p.charge_id }}</code></span>
              <span>
                {{ formatPrice(p.amount_cents) }}
                <Tag :value="p.status" :severity="p.status === 'succeeded' ? 'success' : p.status === 'failed' ? 'danger' : 'secondary'" />
              </span>
            </li>
          </ul>
        </section>
      </div>

      <section class="card">
        <h2>History</h2>
        <p v-if="order.history.length === 0" class="muted">No recorded events.</p>
        <ol class="history">
          <li v-for="(event, i) in order.history" :key="i">
            <span class="history__desc">{{ event.description }}</span>
            <span v-if="event.properties.from" class="muted">
              {{ event.properties.from }} → {{ event.properties.to }}
            </span>
            <span class="muted">{{ formatWhen(event.created_at) }}</span>
          </li>
        </ol>
      </section>
    </template>
  </section>
</template>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: start; gap: var(--space-4); margin-bottom: var(--space-5); }
.back { font-size: var(--text-sm); color: var(--color-text-muted); text-decoration: none; }
.head h1 { margin: var(--space-2) 0 var(--space-1); font-size: var(--text-2xl); display: flex; gap: var(--space-3); align-items: center; }
.sub { color: var(--color-text-muted); font-size: var(--text-sm); }
.actions { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: var(--space-5); margin-bottom: var(--space-5); }
.card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-5); }
.card h2 { font-size: var(--text-sm); text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-muted); margin: 0 0 var(--space-3); }
.card h2 + h2, .address + h2 { margin-top: var(--space-5); }
.lines { list-style: none; margin: 0; padding: 0; }
.lines li { display: flex; justify-content: space-between; gap: var(--space-3); padding: var(--space-2) 0; border-bottom: 1px solid var(--color-border); font-size: var(--text-sm); }
.breakdown { margin: var(--space-3) 0 0; }
.breakdown div { display: flex; justify-content: space-between; padding: var(--space-1) 0; font-size: var(--text-sm); }
.breakdown__total { border-top: 1px solid var(--color-border); font-weight: 600; }
.breakdown dt { color: var(--color-text-muted); }
.breakdown dd { margin: 0; }
.address { font-style: normal; line-height: 1.6; margin-bottom: var(--space-3); }
.history { list-style: none; margin: 0; padding: 0; }
.history li { display: flex; gap: var(--space-4); padding: var(--space-2) 0; border-bottom: 1px solid var(--color-border); font-size: var(--text-sm); }
.history__desc { font-weight: 600; }
.muted { color: var(--color-text-muted); font-size: var(--text-sm); }
.notice { color: var(--color-danger); margin: var(--space-3) 0; }
</style>
