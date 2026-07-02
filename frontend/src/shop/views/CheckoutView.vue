<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import {
  ApiError,
  type CountryCode,
  type Order,
  SHIPPING_COUNTRIES,
  api,
  formatPrice,
} from "../api";
import { useAuth } from "../auth";
import { useCart } from "../cart";

const { state, refresh, checkout } = useCart();
const auth = useAuth();

const placing = ref(false);
const order = ref<Order | null>(null);
const error = ref<string | null>(null);
const fieldErrors = ref<Record<string, string[]>>({});

type PayState = "unpaid" | "processing" | "paid" | "failed";
const payState = ref<PayState>("unpaid");
const payError = ref<string | null>(null);
let pollTimer: ReturnType<typeof setInterval> | null = null;

function stopPolling() {
  if (pollTimer !== null) clearInterval(pollTimer);
  pollTimer = null;
}

async function payNow() {
  if (!order.value) return;
  payState.value = "processing";
  payError.value = null;
  const { id, token } = order.value;
  try {
    await api.pay(id, token);
  } catch {
    payState.value = "failed";
    payError.value = "We couldn't start the payment. Please try again.";
    return;
  }
  // the gateway confirms asynchronously (webhook) — poll the order until it flips
  let attempts = 0;
  stopPolling();
  pollTimer = setInterval(async () => {
    attempts += 1;
    const fresh = await api.order(id, token);
    order.value = fresh;
    if (fresh.status === "paid") {
      payState.value = "paid";
      stopPolling();
    } else if (fresh.payment_status === "failed") {
      payState.value = "failed";
      payError.value = "The payment didn't go through. You can try again.";
      stopPolling();
    } else if (attempts >= 20) {
      payState.value = "failed";
      payError.value = "Payment is taking longer than expected — check your account shortly.";
      stopPolling();
    }
  }, 1000);
}

onBeforeUnmount(stopPolling);

const form = reactive({
  email: "",
  name: "",
  line1: "",
  line2: "",
  city: "",
  postal_code: "",
  country: "US" as CountryCode,
});

const signedIn = computed(() => auth.state.customer !== null);

function fieldError(field: string): string | null {
  return fieldErrors.value[field]?.[0] ?? null;
}

async function placeOrder() {
  placing.value = true;
  error.value = null;
  fieldErrors.value = {};
  try {
    order.value = await checkout({
      ...(form.email ? { email: form.email } : {}),
      address: {
        name: form.name,
        line1: form.line1,
        line2: form.line2 || null,
        city: form.city,
        postal_code: form.postal_code,
        country: form.country,
      },
    });
  } catch (e) {
    if (e instanceof ApiError && e.status === 422 && Object.keys(e.errors).length > 0) {
      fieldErrors.value = e.errors;
      error.value = "Please check the highlighted fields.";
    } else {
      error.value = "We couldn't place your order. Please try again.";
    }
  } finally {
    placing.value = false;
  }
}

onMounted(async () => {
  await refresh();
  await auth.restore();
  if (auth.state.customer) {
    form.email = auth.state.customer.email;
    form.name = auth.state.customer.name;
  }
});
</script>

<template>
  <main class="checkout">
    <div v-if="order" class="confirm">
      <div class="confirm__mark" aria-hidden="true">✓</div>
      <p class="eyebrow">Thank you</p>
      <h1>Order placed</h1>
      <p class="confirm__line">
        Order <strong>#{{ order.id }}</strong>
        <span class="confirm__status">{{ order.status }}</span>
      </p>
      <dl class="breakdown">
        <div><dt>Subtotal</dt><dd>{{ formatPrice(order.subtotal_cents) }}</dd></div>
        <div><dt>Shipping</dt><dd>{{ formatPrice(order.shipping_cents) }}</dd></div>
        <div><dt>Tax</dt><dd>{{ formatPrice(order.tax_cents) }}</dd></div>
        <div class="breakdown__total"><dt>Total</dt><dd>{{ formatPrice(order.total_cents) }}</dd></div>
      </dl>
      <p class="confirm__note">
        Shipping to {{ order.address.name }}, {{ order.address.line1 }}, {{ order.address.city }}.
      </p>
      <p class="confirm__note">A confirmation was sent to {{ order.contact_email }}.</p>

      <section class="pay" aria-live="polite">
        <template v-if="payState === 'paid' || order.status === 'paid'">
          <p class="pay__done">✓ Paid — thank you!</p>
        </template>
        <template v-else-if="payState === 'processing'">
          <p class="pay__processing">Processing your payment…</p>
        </template>
        <template v-else>
          <p v-if="payError" class="error" role="alert">{{ payError }}</p>
          <button class="btn btn--primary pay__button" @click="payNow">
            {{ payState === "failed" ? "Try payment again" : `Pay ${formatPrice(order.total_cents)}` }}
          </button>
        </template>
      </section>

      <RouterLink class="btn" to="/">Continue shopping</RouterLink>
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

      <form v-else class="panel" novalidate @submit.prevent="placeOrder">
        <ul class="lines">
          <li v-for="line in state.cart.items" :key="line.id">
            <span>{{ line.quantity }} × Variant #{{ line.product_variant_id }}</span>
            <span>{{ formatPrice(line.line_total_cents) }}</span>
          </li>
        </ul>
        <div class="total"><span>Subtotal</span><strong>{{ formatPrice(state.cart.total_cents) }}</strong></div>
        <p class="fineprint">Shipping and tax are calculated when you place the order.</p>

        <fieldset class="fields">
          <legend>Contact</legend>
          <label>
            <span>Email {{ signedIn ? "" : "(for your order updates)" }}</span>
            <input v-model.trim="form.email" type="email" autocomplete="email" :aria-invalid="!!fieldError('email')" />
            <small v-if="fieldError('email')" class="field-error" role="alert">{{ fieldError("email") }}</small>
          </label>
        </fieldset>

        <fieldset class="fields">
          <legend>Shipping address</legend>
          <label>
            <span>Full name</span>
            <input v-model.trim="form.name" type="text" autocomplete="name" :aria-invalid="!!fieldError('name')" />
            <small v-if="fieldError('name')" class="field-error" role="alert">{{ fieldError("name") }}</small>
          </label>
          <label>
            <span>Address line 1</span>
            <input v-model.trim="form.line1" type="text" autocomplete="address-line1" :aria-invalid="!!fieldError('line1')" />
            <small v-if="fieldError('line1')" class="field-error" role="alert">{{ fieldError("line1") }}</small>
          </label>
          <label>
            <span>Address line 2 <em>(optional)</em></span>
            <input v-model.trim="form.line2" type="text" autocomplete="address-line2" />
          </label>
          <div class="fields__row">
            <label>
              <span>City</span>
              <input v-model.trim="form.city" type="text" autocomplete="address-level2" :aria-invalid="!!fieldError('city')" />
              <small v-if="fieldError('city')" class="field-error" role="alert">{{ fieldError("city") }}</small>
            </label>
            <label>
              <span>Postal code</span>
              <input v-model.trim="form.postal_code" type="text" autocomplete="postal-code" :aria-invalid="!!fieldError('postal_code')" />
              <small v-if="fieldError('postal_code')" class="field-error" role="alert">{{ fieldError("postal_code") }}</small>
            </label>
          </div>
          <label>
            <span>Country</span>
            <select v-model="form.country" autocomplete="country" :aria-invalid="!!fieldError('country')">
              <option v-for="c in SHIPPING_COUNTRIES" :key="c.code" :value="c.code">{{ c.label }}</option>
            </select>
            <small v-if="fieldError('country')" class="field-error" role="alert">{{ fieldError("country") }}</small>
          </label>
        </fieldset>

        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="btn btn--primary place" :disabled="placing" type="submit">
          {{ placing ? "Placing order…" : "Place order" }}
        </button>
        <p class="fineprint">Payment is collected after your order is placed.</p>
      </form>
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
.total { display: flex; justify-content: space-between; align-items: baseline; font-size: var(--text-lg); margin: var(--space-5) 0 var(--space-2); }
.fields { border: 0; margin: var(--space-6) 0 0; padding: 0; }
.fields legend { font-size: var(--text-sm); font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; color: var(--color-text-muted); margin-bottom: var(--space-3); }
.fields label { display: block; margin-bottom: var(--space-4); }
.fields label span { display: block; font-size: var(--text-sm); margin-bottom: var(--space-1); }
.fields label em { color: var(--color-text-muted); font-style: normal; }
.fields input, .fields select { width: 100%; padding: var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); color: var(--color-text); font: inherit; }
.fields input[aria-invalid="true"], .fields select[aria-invalid="true"] { border-color: var(--color-danger); }
.fields__row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); }
.field-error { display: block; color: var(--color-danger); font-size: var(--text-xs); margin-top: var(--space-1); }
.breakdown { margin: var(--space-6) auto var(--space-4); max-width: 320px; text-align: left; }
.breakdown div { display: flex; justify-content: space-between; padding: var(--space-2) 0; font-size: var(--text-sm); }
.breakdown__total { border-top: 1px solid var(--color-border); font-weight: 600; font-size: var(--text-base); }
.breakdown dt { color: var(--color-text-muted); }
.breakdown dd { margin: 0; }
.error { color: var(--color-danger); font-size: var(--text-sm); margin-top: var(--space-4); }
.pay { margin: var(--space-6) 0; }
.pay__button { padding: var(--space-4) var(--space-8); }
.pay__done { color: var(--color-success, #2e7d32); font-weight: 600; }
.pay__processing { color: var(--color-text-muted); }
.place { width: 100%; padding: var(--space-4); margin-top: var(--space-4); }
.fineprint { font-size: var(--text-xs); color: var(--color-text-muted); text-align: center; margin: var(--space-2) 0 0; }
</style>
