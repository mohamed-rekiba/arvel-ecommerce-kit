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
    <!-- confirmation -->
    <div v-if="order" class="confirm">
      <div class="confirm__mark" aria-hidden="true">✓</div>
      <h1>Order placed</h1>
      <p>Order <strong>#{{ order.id }}</strong> — {{ formatPrice(order.total_cents) }} ({{ order.status }}).</p>
      <RouterLink class="btn btn--primary" to="/">Continue shopping</RouterLink>
    </div>

    <template v-else>
      <h1>Checkout</h1>
      <div v-if="!state.cart || state.cart.items.length === 0" class="state">
        <p>Your cart is empty.</p>
        <RouterLink class="btn" to="/">Browse the shop</RouterLink>
      </div>
      <template v-else>
        <ul class="checkout__lines">
          <li v-for="line in state.cart.items" :key="line.id">
            <span>{{ line.quantity }} × variant #{{ line.product_variant_id }}</span>
            <span>{{ formatPrice(line.line_total_cents) }}</span>
          </li>
        </ul>
        <div class="checkout__total">
          <span>Total</span><strong>{{ formatPrice(state.cart.total_cents) }}</strong>
        </div>
        <p v-if="error" class="checkout__error" role="alert">{{ error }}</p>
        <button class="btn btn--primary" :disabled="placing" @click="placeOrder">
          {{ placing ? "Placing…" : "Place order" }}
        </button>
      </template>
    </template>
  </main>
</template>

<style scoped>
.checkout { max-width: 560px; margin: 0 auto; padding: var(--space-8) var(--container-pad); }
.checkout h1 { font-size: var(--text-2xl); margin-bottom: var(--space-6); }
.checkout__lines { list-style: none; margin: 0 0 var(--space-4); padding: 0; }
.checkout__lines li { display: flex; justify-content: space-between; padding: var(--space-3) 0; border-bottom: 1px solid var(--color-border); }
.checkout__total { display: flex; justify-content: space-between; font-size: var(--text-lg); margin: var(--space-4) 0 var(--space-6); }
.checkout__error { color: var(--color-danger, #b00020); }
.btn { display: inline-block; padding: var(--space-3) var(--space-5); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); cursor: pointer; font: inherit; text-decoration: none; color: var(--color-text); }
.btn--primary { background: var(--color-accent); color: var(--color-text-inverse); border-color: var(--color-accent); width: 100%; }
.btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
.state { text-align: center; color: var(--color-text-muted); }
.confirm { text-align: center; padding: var(--space-12) 0; }
.confirm__mark { width: 3.5rem; height: 3.5rem; margin: 0 auto var(--space-4); border-radius: var(--radius-full); background: var(--color-accent); color: var(--color-text-inverse); font-size: var(--text-2xl); line-height: 3.5rem; }
.confirm h1 { font-size: var(--text-2xl); }
</style>
