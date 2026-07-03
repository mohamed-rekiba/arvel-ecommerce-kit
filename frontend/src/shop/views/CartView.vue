<script setup lang="ts">
import { t } from "../locale";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError, formatPrice } from "../api";
import { useCart } from "../cart";

const router = useRouter();
const couponCode = ref("");
const couponError = ref<string | null>(null);

async function submitCoupon() {
  couponError.value = null;
  try {
    await applyCoupon(couponCode.value);
    couponCode.value = "";
  } catch (e) {
    couponError.value =
      e instanceof ApiError ? Object.values(e.errors)[0]?.[0] ?? t("cart.coupon_error") : t("cart.coupon_error");
  }
}

async function dropCoupon() {
  couponError.value = null;
  await removeCoupon();
}

const { state, refresh, update, remove, applyCoupon, removeCoupon } = useCart();

onMounted(refresh);
</script>

<template>
  <main class="cart">
    <header class="cart__head">
      <p class="eyebrow">{{ t("cart.eyebrow") }}</p>
      <h1>{{ t("cart.title") }}</h1>
    </header>

    <div v-if="state.loading" class="state" aria-busy="true">{{ t("common.loading") }}</div>

    <div v-else-if="!state.cart || state.cart.items.length === 0" class="state">
      <p>{{ t("cart.empty") }}</p>
      <RouterLink class="btn btn--primary" to="/">{{ t("cart.browse") }}</RouterLink>
    </div>

    <div v-else class="cart__grid">
      <ul class="lines">
        <li v-for="line in state.cart.items" :key="line.id" class="line">
          <div class="line__thumb">
            <img v-if="line.image_url" :src="line.image_url" :alt="line.product_name" />
          </div>
          <div class="line__meta">
            <span class="line__name">{{ line.product_name }}</span>
            <span class="line__variant">{{ line.variant_name }}</span>
            <span class="line__unit">{{ t("cart.each", { price: formatPrice(line.unit_price_cents) }) }}</span>
            <button class="line__remove" @click="remove(line.id)">{{ t("cart.remove") }}</button>
          </div>
          <div class="qty" role="group" :aria-label="t('cart.quantity')">
            <button :aria-label="t('cart.decrease')" @click="update(line.id, Math.max(1, line.quantity - 1))">−</button>
            <span>{{ line.quantity }}</span>
            <button :aria-label="t('cart.increase')" @click="update(line.id, line.quantity + 1)">+</button>
          </div>
          <span class="line__total">{{ formatPrice(line.line_total_cents) }}</span>
        </li>
      </ul>

      <aside class="summary">
        <h2 class="summary__title">{{ t("cart.summary") }}</h2>
        <div class="summary__row"><span>{{ t("checkout.subtotal") }}</span><span>{{ formatPrice(state.cart.total_cents) }}</span></div>

        <div v-if="state.cart.coupon_code" class="summary__row summary__row--discount">
          <span>
            {{ t("cart.code") }} <strong>{{ state.cart.coupon_code }}</strong>
            <button class="coupon__remove" @click="dropCoupon">{{ t("cart.remove_lc") }}</button>
          </span>
          <span>−{{ formatPrice(state.cart.discount_cents) }}</span>
        </div>
        <form v-else class="coupon" @submit.prevent="submitCoupon">
          <input
            v-model.trim="couponCode"
            type="text"
            :placeholder="t('cart.discount_code')"
            :aria-label="t('cart.discount_code')"
          />
          <button class="btn" type="submit" :disabled="!couponCode">{{ t("cart.apply") }}</button>
        </form>
        <p v-if="couponError" class="coupon__error" role="alert">{{ couponError }}</p>

        <div class="summary__row summary__row--muted"><span>{{ t("cart.shipping") }}</span><span>{{ t("cart.at_checkout") }}</span></div>
        <div class="summary__row summary__row--total"><span>{{ t("cart.total") }}</span><strong>{{ formatPrice(state.cart.total_cents - state.cart.discount_cents) }}</strong></div>
        <button class="btn btn--primary summary__cta" @click="router.push('/checkout')">{{ t("cart.checkout") }}</button>
        <RouterLink class="summary__cont" to="/">{{ t("cart.continue") }}</RouterLink>
      </aside>
    </div>
  </main>
</template>

<style scoped>
.cart { max-width: var(--container-max); margin: 0 auto; padding: var(--space-12) var(--container-pad) 0; }
.cart__head { margin-bottom: var(--space-10); }
.cart__head h1 { font-size: var(--text-3xl); margin-top: var(--space-2); }
.cart__grid { display: grid; grid-template-columns: 1fr; gap: var(--space-8); align-items: start; }
@media (min-width: 1024px) { .cart__grid { grid-template-columns: 1fr 340px; gap: var(--space-12); } }
.lines { list-style: none; margin: 0; padding: 0; }
/* Mobile base: thumb spans both rows in col 1, meta sits above the qty stepper in col 2, price sits in
   col 3 spanning both rows — avoids cramming a 4-across desktop row into a narrow phone width. */
.line {
  display: grid;
  grid-template-columns: 56px 1fr auto;
  column-gap: var(--space-3); row-gap: var(--space-2);
  align-items: center; padding: var(--space-4) 0;
  border-top: 1px solid var(--color-border);
}
.line:last-child { border-bottom: 1px solid var(--color-border); }
.line__thumb { grid-column: 1; grid-row: 1 / 3; width: 56px; aspect-ratio: 3 / 4; background: var(--photo-well); border-radius: var(--radius-sm); overflow: hidden; border: 1px solid var(--border); }
.line__thumb img { width: 100%; height: 100%; object-fit: cover; }
[data-theme="dark"] .line__thumb img { filter: brightness(.88); }
.line__variant { font-size: var(--text-xs); color: var(--color-text-muted); }
.line__meta { grid-column: 2; grid-row: 1; display: flex; flex-direction: column; gap: 2px; }
.qty { grid-column: 2; grid-row: 2; justify-self: start; }
.line__total { grid-column: 3; grid-row: 1 / 3; }
@media (min-width: 640px) {
  .line { grid-template-columns: 72px 1fr auto auto; column-gap: var(--space-4); row-gap: 0; padding: var(--space-5) 0; }
  .line__thumb { width: 72px; grid-row: auto; }
  .line__meta { grid-row: auto; }
  .qty { grid-column: auto; grid-row: auto; justify-self: auto; }
  .line__total { grid-column: auto; grid-row: auto; }
}
.line__name { font-family: var(--font-display); font-size: var(--text-lg); }
.line__unit { font-size: var(--text-sm); color: var(--color-text-muted); }
.line__remove { align-self: flex-start; margin-top: var(--space-1); border: none; background: none; padding: 0; color: var(--color-text-muted); font-size: var(--text-sm); cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
.line__remove:hover { color: var(--color-text); }
.qty { display: inline-flex; align-items: center; gap: var(--space-3); border: 1px solid var(--color-border-strong); border-radius: var(--radius-full); padding: var(--space-1) var(--space-2); }
.qty button { width: 1.75rem; height: 1.75rem; border: none; background: none; cursor: pointer; font-size: var(--text-lg); color: var(--color-text); border-radius: var(--radius-full); }
.qty button:hover { background: var(--color-surface); }
.line__total { font-weight: var(--weight-medium); min-width: 4rem; text-align: end; }
.summary { background: var(--color-surface); border-radius: var(--radius-lg); padding: var(--space-8); }
/* sticky only makes sense once the summary is an actual side column (the ≥1024px 2-col cart__grid) */
@media (min-width: 1024px) { .summary { position: sticky; top: 88px; } }
.summary__title { font-size: var(--text-xl); margin-bottom: var(--space-5); }
.summary__row { display: flex; justify-content: space-between; padding: var(--space-2) 0; font-size: var(--text-sm); }
.summary__row--muted { color: var(--color-text-muted); }
.summary__row--total { border-top: 1px solid var(--color-border-strong); margin-top: var(--space-2); padding-top: var(--space-4); font-size: var(--text-lg); }
.summary__cta { width: 100%; margin-top: var(--space-6); padding: var(--space-4); }
.summary__cont { display: block; text-align: center; margin-top: var(--space-4); font-size: var(--text-sm); color: var(--color-text-muted); text-decoration: none; }
.summary__cont:hover { color: var(--color-text); }
.state { text-align: center; padding: var(--space-20) 0; color: var(--color-text-muted); }
.state .btn { margin-top: var(--space-4); }
.coupon { display: flex; gap: var(--space-2); margin: var(--space-3) 0; }
.coupon input { flex: 1; padding: var(--space-2) var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); color: var(--color-text); font: inherit; }
.coupon__remove { background: none; border: 0; padding: 0; margin-inline-start: var(--space-2); font-size: var(--text-xs); text-decoration: underline; cursor: pointer; color: var(--color-text-muted); }
.coupon__error { color: var(--color-danger); font-size: var(--text-xs); margin: 0 0 var(--space-2); }
.summary__row--discount { color: var(--color-success, #2e7d32); }
</style>
