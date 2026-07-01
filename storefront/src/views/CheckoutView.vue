<script setup lang="ts">
import { onMounted, ref } from "vue";
import { type Order, formatPrice } from "../api";
import { useCart } from "../cart";

const { state, refresh, checkout } = useCart();

const placing = ref(false);
const order = ref<Order | null>(null);
const error = ref<string | null>(null);

async function placeOrder() {
  placing.value = true;
  error.value = null;
  try {
    order.value = await checkout();
  } catch {
    error.value = "We couldn't place your order. Please try again.";
  } finally {
    placing.value = false;
  }
}

onMounted(refresh);
</script>

<template>
  <main class="checkout">
    <div v-if="order" class="confirm">
      <div class="confirm__mark" aria-hidden="true">✓</div>
      <p class="eyebrow">Thank you</p>
      <h1>Order placed</h1>
      <p class="confirm__line">
        Order <strong>#{{ order.id }}</strong> — {{ formatPrice(order.total_cents) }}
        <span class="confirm__status">{{ order.status }}</span>
      </p>
      <p class="confirm__note">A confirmation is on its way. You can close this window.</p>
      <RouterLink class="btn btn--primary" to="/">Continue shopping</RouterLink>
    </div>

    <template v-else>
      <header class="checkout__head">
        <p class="eyebrow">Almost there</p>
        <h1>Checkout</h1>
      </header>

      <div v-if="!state.cart || state.cart.items.length === 0" class="state">
        <p>Your cart is empty.</p>
        <RouterLink class="btn btn--primary" to="/">Browse the collection</RouterLink>
      </div>

      <div v-else class="panel">
        <ul class="lines">
          <li v-for="line in state.cart.items" :key="line.id">
            <span>{{ line.quantity }} × Variant #{{ line.product_variant_id }}</span>
            <span>{{ formatPrice(line.line_total_cents) }}</span>
          </li>
        </ul>
        <div class="total"><span>Total</span><strong>{{ formatPrice(state.cart.total_cents) }}</strong></div>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="btn btn--primary place" :disabled="placing" @click="placeOrder">
          {{ placing ? "Placing order…" : "Place order" }}
        </button>
        <p class="fineprint">Demo checkout — no payment is taken. Placing an order exercises the real order pipeline.</p>
      </div>
    </template>
  </main>
</template>

<style scoped>
.checkout { max-width: 560px; margin: 0 auto; padding: var(--space-16) var(--container-pad) 0; }
.checkout__head { margin-bottom: var(--space-8); }
.checkout__head h1 { font-size: var(--text-3xl); margin-top: var(--space-2); }
.panel { background: var(--color-surface); border-radius: var(--radius-lg); padding: var(--space-8); }
.lines { list-style: none; margin: 0 0 var(--space-4); padding: 0; }
.lines li { display: flex; justify-content: space-between; padding: var(--space-3) 0; border-bottom: 1px solid var(--color-border); font-size: var(--text-sm); }
.total { display: flex; justify-content: space-between; align-items: baseline; font-size: var(--text-lg); margin: var(--space-5) 0 var(--space-6); }
.error { color: var(--color-danger); font-size: var(--text-sm); }
.place { width: 100%; padding: var(--space-4); }
.fineprint { font-size: var(--text-xs); color: var(--color-text-muted); text-align: center; margin: var(--space-4) 0 0; }
.state { text-align: center; color: var(--color-text-muted); padding: var(--space-8) 0; }
.state .btn { margin-top: var(--space-4); }
.confirm { text-align: center; padding: var(--space-16) 0; }
.confirm__mark { width: 3.5rem; height: 3.5rem; margin: 0 auto var(--space-6); border-radius: var(--radius-full); background: var(--color-accent); color: var(--color-text-inverse); font-size: var(--text-2xl); display: grid; place-items: center; }
.confirm h1 { font-size: var(--text-3xl); margin: var(--space-2) 0 var(--space-4); }
.confirm__line { font-size: var(--text-lg); }
.confirm__status { display: inline-block; margin-left: var(--space-2); padding: 2px var(--space-3); background: var(--color-accent-soft); color: var(--color-accent); border-radius: var(--radius-full); font-size: var(--text-xs); text-transform: capitalize; }
.confirm__note { color: var(--color-text-muted); margin: var(--space-4) 0 var(--space-8); }
</style>
