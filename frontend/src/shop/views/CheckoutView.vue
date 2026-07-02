<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import {
  ApiError,
  type CountryCode,
  type Order,
  SHIPPING_COUNTRY_CODES,
  api,
  formatPrice,
} from "../api";
import { type MessageKey, t } from "../locale";
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
    payError.value = t("checkout.pay_start_error");
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
      payError.value = t("checkout.pay_failed");
      stopPolling();
    } else if (attempts >= 20) {
      payState.value = "failed";
      payError.value = t("checkout.pay_slow");
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
      error.value = t("checkout.check_fields");
    } else {
      error.value = t("checkout.place_error");
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
      <p class="eyebrow">{{ t("checkout.thanks") }}</p>
      <h1>{{ t("checkout.placed") }}</h1>
      <p class="confirm__line">
        {{ t("checkout.order") }} <strong>#{{ order.id }}</strong>
        <span class="confirm__status">{{ t(`order.${order.status}` as MessageKey) }}</span>
      </p>
      <dl class="breakdown">
        <div><dt>{{ t("checkout.subtotal") }}</dt><dd>{{ formatPrice(order.subtotal_cents) }}</dd></div>
        <div><dt>{{ t("cart.shipping") }}</dt><dd>{{ formatPrice(order.shipping_cents) }}</dd></div>
        <div><dt>{{ t("checkout.tax") }}</dt><dd>{{ formatPrice(order.tax_cents) }}</dd></div>
        <div v-if="order.discount_cents > 0"><dt>{{ t("checkout.discount") }} ({{ order.coupon_code }})</dt><dd>−{{ formatPrice(order.discount_cents) }}</dd></div>
        <div class="breakdown__total"><dt>{{ t("cart.total") }}</dt><dd>{{ formatPrice(order.total_cents) }}</dd></div>
      </dl>
      <p class="confirm__note">
        {{ t("checkout.shipping_to", { name: order.address.name, line1: order.address.line1, city: order.address.city }) }}
      </p>
      <p class="confirm__note">{{ t("checkout.confirmation_sent", { email: order.contact_email }) }}</p>

      <section class="pay" aria-live="polite">
        <template v-if="payState === 'paid' || order.status === 'paid'">
          <p class="pay__done">✓ {{ t("checkout.paid") }}</p>
        </template>
        <template v-else-if="payState === 'processing'">
          <p class="pay__processing">{{ t("checkout.processing") }}</p>
        </template>
        <template v-else>
          <p v-if="payError" class="error" role="alert">{{ payError }}</p>
          <button class="btn btn--primary pay__button" @click="payNow">
            {{ payState === "failed" ? t("checkout.pay_retry") : t("checkout.pay_now", { total: formatPrice(order.total_cents) }) }}
          </button>
        </template>
      </section>

      <RouterLink class="btn btn--primary" :to="`/orders/${order.id}`">{{ t("checkout.view_order") }}</RouterLink>
      <RouterLink class="btn" to="/">{{ t("cart.continue") }}</RouterLink>
    </div>

    <template v-else>
      <header class="checkout__head">
        <p class="eyebrow">{{ t("checkout.eyebrow") }}</p>
        <h1>{{ t("checkout.title") }}</h1>
      </header>

      <div v-if="!state.cart || state.cart.items.length === 0" class="state">
        <p>{{ t("cart.empty") }}</p>
        <RouterLink class="btn btn--primary" to="/">{{ t("cart.browse") }}</RouterLink>
      </div>

      <form v-else class="panel" novalidate @submit.prevent="placeOrder">
        <ul class="lines">
          <li v-for="line in state.cart.items" :key="line.id">
            <span>{{ line.quantity }} × {{ t("cart.variant_n", { n: line.product_variant_id }) }}</span>
            <span>{{ formatPrice(line.line_total_cents) }}</span>
          </li>
        </ul>
        <div class="total"><span>{{ t("checkout.subtotal") }}</span><strong>{{ formatPrice(state.cart.total_cents) }}</strong></div>
        <p class="fineprint">{{ t("checkout.fineprint_totals") }}</p>

        <fieldset class="fields">
          <legend>{{ t("checkout.contact") }}</legend>
          <label>
            <span>{{ t("checkout.email") }} {{ signedIn ? "" : t("checkout.email_hint") }}</span>
            <input v-model.trim="form.email" type="email" autocomplete="email" :aria-invalid="!!fieldError('email')" />
            <small v-if="fieldError('email')" class="field-error" role="alert">{{ fieldError("email") }}</small>
          </label>
        </fieldset>

        <fieldset class="fields">
          <legend>{{ t("checkout.address") }}</legend>
          <label>
            <span>{{ t("checkout.full_name") }}</span>
            <input v-model.trim="form.name" type="text" autocomplete="name" :aria-invalid="!!fieldError('name')" />
            <small v-if="fieldError('name')" class="field-error" role="alert">{{ fieldError("name") }}</small>
          </label>
          <label>
            <span>{{ t("checkout.line1") }}</span>
            <input v-model.trim="form.line1" type="text" autocomplete="address-line1" :aria-invalid="!!fieldError('line1')" />
            <small v-if="fieldError('line1')" class="field-error" role="alert">{{ fieldError("line1") }}</small>
          </label>
          <label>
            <span>{{ t("checkout.line2") }} <em>{{ t("common.optional") }}</em></span>
            <input v-model.trim="form.line2" type="text" autocomplete="address-line2" />
          </label>
          <div class="fields__row">
            <label>
              <span>{{ t("checkout.city") }}</span>
              <input v-model.trim="form.city" type="text" autocomplete="address-level2" :aria-invalid="!!fieldError('city')" />
              <small v-if="fieldError('city')" class="field-error" role="alert">{{ fieldError("city") }}</small>
            </label>
            <label>
              <span>{{ t("checkout.postal") }}</span>
              <input v-model.trim="form.postal_code" type="text" autocomplete="postal-code" :aria-invalid="!!fieldError('postal_code')" />
              <small v-if="fieldError('postal_code')" class="field-error" role="alert">{{ fieldError("postal_code") }}</small>
            </label>
          </div>
          <label>
            <span>{{ t("checkout.country") }}</span>
            <select v-model="form.country" autocomplete="country" :aria-invalid="!!fieldError('country')">
              <option v-for="c in SHIPPING_COUNTRY_CODES" :key="c" :value="c">{{ t(`country.${c}` as MessageKey) }}</option>
            </select>
            <small v-if="fieldError('country')" class="field-error" role="alert">{{ fieldError("country") }}</small>
          </label>
        </fieldset>

        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="btn btn--primary place" :disabled="placing" type="submit">
          {{ placing ? "…" : t("checkout.place") }}
        </button>
        <p class="fineprint">{{ t("checkout.fineprint_payment") }}</p>
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
.breakdown { margin: var(--space-6) auto var(--space-4); max-width: 320px; text-align: start; }
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
