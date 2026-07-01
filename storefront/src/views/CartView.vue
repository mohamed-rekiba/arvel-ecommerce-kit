<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { formatPrice } from "../api";
import { useCart } from "../cart";

const router = useRouter();
const { state, refresh, update, remove } = useCart();

onMounted(refresh);
</script>

<template>
  <main class="cart">
    <h1>Your cart</h1>

    <div v-if="state.loading" class="state" aria-busy="true">Loading…</div>

    <div v-else-if="!state.cart || state.cart.items.length === 0" class="state">
      <p>Your cart is empty.</p>
      <RouterLink class="btn" to="/">Browse the shop</RouterLink>
    </div>

    <template v-else>
      <ul class="cart__lines">
        <li v-for="line in state.cart.items" :key="line.id" class="cart__line">
          <div class="cart__meta">
            <span class="cart__variant">Variant #{{ line.product_variant_id }}</span>
            <span class="cart__unit">{{ formatPrice(line.unit_price_cents) }} each</span>
          </div>
          <div class="cart__qty">
            <button aria-label="decrease" @click="update(line.id, Math.max(1, line.quantity - 1))">−</button>
            <span>{{ line.quantity }}</span>
            <button aria-label="increase" @click="update(line.id, line.quantity + 1)">+</button>
          </div>
          <span class="cart__total">{{ formatPrice(line.line_total_cents) }}</span>
          <button class="cart__remove" aria-label="remove" @click="remove(line.id)">✕</button>
        </li>
      </ul>

      <div class="cart__summary">
        <span>Subtotal</span>
        <strong>{{ formatPrice(state.cart.total_cents) }}</strong>
      </div>
      <button class="btn btn--primary" @click="router.push('/checkout')">Checkout</button>
    </template>
  </main>
</template>

<style scoped>
.cart { max-width: 720px; margin: 0 auto; padding: var(--space-8) var(--container-pad); }
.cart h1 { font-size: var(--text-2xl); margin-bottom: var(--space-6); }
.cart__lines { list-style: none; margin: 0; padding: 0; }
.cart__line { display: grid; grid-template-columns: 1fr auto auto auto; align-items: center; gap: var(--space-4); padding: var(--space-4) 0; border-bottom: 1px solid var(--color-border); }
.cart__meta { display: flex; flex-direction: column; }
.cart__variant { font-weight: var(--weight-medium); }
.cart__unit { font-size: var(--text-sm); color: var(--color-text-muted); }
.cart__qty { display: flex; align-items: center; gap: var(--space-2); }
.cart__qty button { width: 2rem; height: 2rem; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); cursor: pointer; }
.cart__total { font-weight: var(--weight-medium); }
.cart__remove { border: none; background: none; color: var(--color-text-muted); cursor: pointer; font-size: var(--text-base); }
.cart__summary { display: flex; justify-content: space-between; align-items: center; margin: var(--space-6) 0; font-size: var(--text-lg); }
.btn { display: inline-block; padding: var(--space-3) var(--space-5); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); cursor: pointer; font: inherit; text-decoration: none; color: var(--color-text); }
.btn--primary { background: var(--color-accent); color: var(--color-text-inverse); border-color: var(--color-accent); width: 100%; }
.state { text-align: center; color: var(--color-text-muted); padding: var(--space-8) 0; }
</style>
