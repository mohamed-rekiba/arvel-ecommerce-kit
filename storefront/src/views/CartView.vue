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
    <header class="cart__head">
      <p class="eyebrow">Your bag</p>
      <h1>Cart</h1>
    </header>

    <div v-if="state.loading" class="state" aria-busy="true">Loading…</div>

    <div v-else-if="!state.cart || state.cart.items.length === 0" class="state">
      <p>Your cart is empty.</p>
      <RouterLink class="btn btn--primary" to="/">Browse the collection</RouterLink>
    </div>

    <div v-else class="cart__grid">
      <ul class="lines">
        <li v-for="line in state.cart.items" :key="line.id" class="line">
          <div class="line__thumb" aria-hidden="true" />
          <div class="line__meta">
            <span class="line__name">Variant #{{ line.product_variant_id }}</span>
            <span class="line__unit">{{ formatPrice(line.unit_price_cents) }} each</span>
            <button class="line__remove" @click="remove(line.id)">Remove</button>
          </div>
          <div class="qty" role="group" aria-label="Quantity">
            <button aria-label="decrease" @click="update(line.id, Math.max(1, line.quantity - 1))">−</button>
            <span>{{ line.quantity }}</span>
            <button aria-label="increase" @click="update(line.id, line.quantity + 1)">+</button>
          </div>
          <span class="line__total">{{ formatPrice(line.line_total_cents) }}</span>
        </li>
      </ul>

      <aside class="summary">
        <h2 class="summary__title">Summary</h2>
        <div class="summary__row"><span>Subtotal</span><span>{{ formatPrice(state.cart.total_cents) }}</span></div>
        <div class="summary__row summary__row--muted"><span>Shipping</span><span>Calculated at checkout</span></div>
        <div class="summary__row summary__row--total"><span>Total</span><strong>{{ formatPrice(state.cart.total_cents) }}</strong></div>
        <button class="btn btn--primary summary__cta" @click="router.push('/checkout')">Checkout</button>
        <RouterLink class="summary__cont" to="/">Continue shopping</RouterLink>
      </aside>
    </div>
  </main>
</template>

<style scoped>
.cart { max-width: var(--container-max); margin: 0 auto; padding: var(--space-12) var(--container-pad) 0; }
.cart__head { margin-bottom: var(--space-10); }
.cart__head h1 { font-size: var(--text-3xl); margin-top: var(--space-2); }
.cart__grid { display: grid; grid-template-columns: 1fr 340px; gap: var(--space-12); align-items: start; }
@media (max-width: 820px) { .cart__grid { grid-template-columns: 1fr; gap: var(--space-8); } }
.lines { list-style: none; margin: 0; padding: 0; }
.line { display: grid; grid-template-columns: 72px 1fr auto auto; align-items: center; gap: var(--space-4); padding: var(--space-5) 0; border-top: 1px solid var(--color-border); }
.line:last-child { border-bottom: 1px solid var(--color-border); }
.line__thumb { width: 72px; aspect-ratio: 3 / 4; background: var(--color-surface); border-radius: var(--radius-sm); }
.line__meta { display: flex; flex-direction: column; gap: 2px; }
.line__name { font-family: var(--font-display); font-size: var(--text-lg); }
.line__unit { font-size: var(--text-sm); color: var(--color-text-muted); }
.line__remove { align-self: flex-start; margin-top: var(--space-1); border: none; background: none; padding: 0; color: var(--color-text-muted); font-size: var(--text-sm); cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
.line__remove:hover { color: var(--color-text); }
.qty { display: inline-flex; align-items: center; gap: var(--space-3); border: 1px solid var(--color-border-strong); border-radius: var(--radius-full); padding: var(--space-1) var(--space-2); }
.qty button { width: 1.75rem; height: 1.75rem; border: none; background: none; cursor: pointer; font-size: var(--text-lg); color: var(--color-text); border-radius: var(--radius-full); }
.qty button:hover { background: var(--color-surface); }
.line__total { font-weight: var(--weight-medium); min-width: 4rem; text-align: right; }
.summary { background: var(--color-surface); border-radius: var(--radius-lg); padding: var(--space-8); position: sticky; top: 88px; }
.summary__title { font-size: var(--text-xl); margin-bottom: var(--space-5); }
.summary__row { display: flex; justify-content: space-between; padding: var(--space-2) 0; font-size: var(--text-sm); }
.summary__row--muted { color: var(--color-text-muted); }
.summary__row--total { border-top: 1px solid var(--color-border-strong); margin-top: var(--space-2); padding-top: var(--space-4); font-size: var(--text-lg); }
.summary__cta { width: 100%; margin-top: var(--space-6); padding: var(--space-4); }
.summary__cont { display: block; text-align: center; margin-top: var(--space-4); font-size: var(--text-sm); color: var(--color-text-muted); text-decoration: none; }
.summary__cont:hover { color: var(--color-text); }
.state { text-align: center; padding: var(--space-20) 0; color: var(--color-text-muted); }
.state .btn { margin-top: var(--space-4); }
</style>
