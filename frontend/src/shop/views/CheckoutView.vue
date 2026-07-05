<script setup lang="ts">
// COD confirmations skip the pay step entirely — see the `isCod` branch in the template below.
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  ApiError,
  type CountryCode,
  type Order,
  SHIPPING_COUNTRY_CODES,
  type SavedAddress,
  api,
  formatPrice
} from '../api'
import { type MessageKey, t } from '../locale'
import { useAuth } from '../auth'
import { useCart } from '../cart'

const { state, refresh, checkout } = useCart()
const auth = useAuth()

const placing = ref(false)
const order = ref<Order | null>(null)
const error = ref<string | null>(null)
const fieldErrors = ref<Record<string, string[]>>({})

// --- saved addresses ---
const saved = ref<SavedAddress[]>([])
const selectedAddress = ref<number | 'new'>('new')
const useSaved = computed(() => selectedAddress.value !== 'new')

// --- payment method ---
const paymentMethod = ref<'gateway' | 'cod'>('gateway')
const isCod = computed(() => order.value?.payment_method === 'cod')

type PayState = 'unpaid' | 'processing' | 'paid' | 'failed'
const payState = ref<PayState>('unpaid')
const payError = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

function stopPolling() {
  if (pollTimer !== null) clearInterval(pollTimer)
  pollTimer = null
}

async function payNow() {
  if (!order.value) return
  payState.value = 'processing'
  payError.value = null
  const { id, token } = order.value
  try {
    await api.pay(id, token)
  } catch {
    payState.value = 'failed'
    payError.value = t('checkout.pay_start_error')
    return
  }
  // the gateway confirms asynchronously (webhook) — poll the order until it flips
  let attempts = 0
  stopPolling()
  pollTimer = setInterval(async () => {
    attempts += 1
    const fresh = await api.order(id, token)
    order.value = fresh
    if (fresh.status === 'paid') {
      payState.value = 'paid'
      stopPolling()
    } else if (fresh.payment_status === 'failed') {
      payState.value = 'failed'
      payError.value = t('checkout.pay_failed')
      stopPolling()
    } else if (attempts >= 20) {
      payState.value = 'failed'
      payError.value = t('checkout.pay_slow')
      stopPolling()
    }
  }, 1000)
}

onBeforeUnmount(stopPolling)

const form = reactive({
  email: '',
  name: '',
  line1: '',
  line2: '',
  city: '',
  postal_code: '',
  country: 'US' as CountryCode
})

const signedIn = computed(() => auth.state.customer !== null)

function fieldError(field: string): string | null {
  return fieldErrors.value[field]?.[0] ?? null
}

async function placeOrder() {
  placing.value = true
  error.value = null
  fieldErrors.value = {}
  try {
    order.value = await checkout({
      ...(form.email ? { email: form.email } : {}),
      ...(useSaved.value
        ? { address_id: selectedAddress.value as number }
        : {
            address: {
              name: form.name,
              line1: form.line1,
              line2: form.line2 || null,
              city: form.city,
              postal_code: form.postal_code,
              country: form.country
            }
          }),
      payment_method: paymentMethod.value
    })
  } catch (e) {
    if (e instanceof ApiError && e.status === 422 && Object.keys(e.errors).length > 0) {
      fieldErrors.value = e.errors
      error.value = t('checkout.check_fields')
    } else {
      error.value = t('checkout.place_error')
    }
  } finally {
    placing.value = false
  }
}

onMounted(async () => {
  await refresh()
  await auth.restore()
  if (auth.state.customer) {
    form.email = auth.state.customer.email
    form.name = auth.state.customer.name
    try {
      saved.value = await api.addresses()
      const dflt = saved.value.find((a) => a.is_default) ?? saved.value[0]
      if (dflt) selectedAddress.value = dflt.id
    } catch {
      saved.value = []
    }
  }
})
</script>

<template>
  <main class="checkout">
    <!-- confirmation -->
    <div v-if="order" class="confirm">
      <div class="confirm__mark" aria-hidden="true">✓</div>
      <p class="eyebrow">{{ t('checkout.thanks') }}</p>
      <h1>{{ t('checkout.placed') }}</h1>
      <p class="confirm__line">
        {{ t('checkout.order') }} <strong>#{{ order.id }}</strong>
        <span class="chip" :class="`chip--${order.status}`">{{
          t(`order.${order.status}` as MessageKey)
        }}</span>
      </p>
      <dl class="breakdown">
        <div>
          <dt>{{ t('checkout.subtotal') }}</dt>
          <dd class="tnum">{{ formatPrice(order.subtotal_cents) }}</dd>
        </div>
        <div>
          <dt>{{ t('cart.shipping') }}</dt>
          <dd class="tnum">{{ formatPrice(order.shipping_cents) }}</dd>
        </div>
        <div>
          <dt>{{ t('checkout.tax') }}</dt>
          <dd class="tnum">{{ formatPrice(order.tax_cents) }}</dd>
        </div>
        <div v-if="order.discount_cents > 0">
          <dt>{{ t('checkout.discount') }} ({{ order.coupon_code }})</dt>
          <dd class="tnum">−{{ formatPrice(order.discount_cents) }}</dd>
        </div>
        <div class="breakdown__total">
          <dt>{{ t('cart.total') }}</dt>
          <dd class="tnum">{{ formatPrice(order.total_cents) }}</dd>
        </div>
      </dl>
      <p class="confirm__note">
        {{
          t('checkout.shipping_to', {
            name: order.address.name,
            line1: order.address.line1,
            city: order.address.city
          })
        }}
      </p>
      <p class="confirm__note">
        {{ t('checkout.confirmation_sent', { email: order.contact_email }) }}
      </p>

      <!-- pay step — gateway orders only; COD gets the heads-up note instead -->
      <section v-if="isCod" class="pay">
        <p class="pay__cod">{{ t('checkout.cod_note') }}</p>
      </section>
      <section v-else class="pay" aria-live="polite">
        <template v-if="payState === 'paid' || order.status === 'paid'">
          <p class="pay__done">✓ {{ t('checkout.paid') }}</p>
        </template>
        <template v-else-if="payState === 'processing'">
          <p class="pay__processing">{{ t('checkout.processing') }}</p>
        </template>
        <template v-else>
          <p v-if="payError" class="error" role="alert">{{ payError }}</p>
          <button class="act act--primary" @click="payNow">
            {{
              payState === 'failed'
                ? t('checkout.pay_retry')
                : t('checkout.pay_now', {
                    total: formatPrice(order.total_cents)
                  })
            }}
          </button>
        </template>
      </section>

      <div class="confirm__links">
        <RouterLink class="act act--primary" :to="`/orders/${order.id}`">{{
          t('checkout.view_order')
        }}</RouterLink>
        <RouterLink class="act" to="/">{{ t('cart.continue') }}</RouterLink>
      </div>
    </div>

    <template v-else>
      <header class="head">
        <p class="eyebrow">{{ t('checkout.eyebrow') }}</p>
        <h1>{{ t('checkout.title') }}</h1>
      </header>

      <div v-if="!state.cart || state.cart.items.length === 0" class="state">
        <p>{{ t('cart.empty') }}</p>
        <RouterLink class="act act--primary" to="/">{{ t('cart.browse') }}</RouterLink>
      </div>

      <form v-else class="panel" novalidate @submit.prevent="placeOrder">
        <ul class="lines">
          <li v-for="line in state.cart.items" :key="line.id" class="line">
            <span class="line__img">
              <img v-if="line.image_url" :src="line.image_url" :alt="line.product_name" />
              <span v-else class="line__ph" aria-hidden="true" />
            </span>
            <span class="line__meta">
              <b>{{ line.product_name }}</b>
              <i>{{ line.variant_name }} · ×{{ line.quantity }}</i>
            </span>
            <span class="line__price tnum">{{ formatPrice(line.line_total_cents) }}</span>
          </li>
        </ul>
        <div class="total">
          <span>{{ t('checkout.subtotal') }}</span
          ><strong class="tnum">{{ formatPrice(state.cart.total_cents) }}</strong>
        </div>
        <p class="fineprint">{{ t('checkout.fineprint_totals') }}</p>

        <fieldset class="fields">
          <legend>{{ t('checkout.contact') }}</legend>
          <label>
            <span>{{ t('checkout.email') }} {{ signedIn ? '' : t('checkout.email_hint') }}</span>
            <input
              v-model.trim="form.email"
              type="email"
              autocomplete="email"
              :aria-invalid="!!fieldError('email')"
            />
            <small v-if="fieldError('email')" class="field-error" role="alert">{{
              fieldError('email')
            }}</small>
          </label>
        </fieldset>

        <!-- saved addresses (signed-in) -->
        <fieldset v-if="saved.length" class="fields">
          <legend>{{ t('checkout.saved_addresses') }}</legend>
          <div class="radios">
            <label
              v-for="a in saved"
              :key="a.id"
              class="radio"
              :class="{ on: selectedAddress === a.id }"
            >
              <input v-model="selectedAddress" type="radio" name="addr" :value="a.id" />
              <span class="radio__meta">
                <b
                  >{{ a.label || a.name }}
                  <em v-if="a.is_default" class="dflt">{{ t('account.addr_default_badge') }}</em></b
                >
                <i>{{ a.line1 }}, {{ a.city }} — {{ a.country }}</i>
              </span>
            </label>
            <label class="radio" :class="{ on: selectedAddress === 'new' }">
              <input v-model="selectedAddress" type="radio" name="addr" value="new" />
              <span class="radio__meta"
                ><b>{{ t('checkout.new_address') }}</b></span
              >
            </label>
          </div>
        </fieldset>

        <fieldset v-if="!useSaved" class="fields">
          <legend>{{ t('checkout.address') }}</legend>
          <label>
            <span>{{ t('checkout.full_name') }}</span>
            <input
              v-model.trim="form.name"
              type="text"
              autocomplete="name"
              :aria-invalid="!!fieldError('name')"
            />
            <small v-if="fieldError('name')" class="field-error" role="alert">{{
              fieldError('name')
            }}</small>
          </label>
          <label>
            <span>{{ t('checkout.line1') }}</span>
            <input
              v-model.trim="form.line1"
              type="text"
              autocomplete="address-line1"
              :aria-invalid="!!fieldError('line1')"
            />
            <small v-if="fieldError('line1')" class="field-error" role="alert">{{
              fieldError('line1')
            }}</small>
          </label>
          <label>
            <span
              >{{ t('checkout.line2') }} <em>{{ t('common.optional') }}</em></span
            >
            <input v-model.trim="form.line2" type="text" autocomplete="address-line2" />
          </label>
          <div class="fields__row">
            <label>
              <span>{{ t('checkout.city') }}</span>
              <input
                v-model.trim="form.city"
                type="text"
                autocomplete="address-level2"
                :aria-invalid="!!fieldError('city')"
              />
              <small v-if="fieldError('city')" class="field-error" role="alert">{{
                fieldError('city')
              }}</small>
            </label>
            <label>
              <span>{{ t('checkout.postal') }}</span>
              <input
                v-model.trim="form.postal_code"
                type="text"
                autocomplete="postal-code"
                :aria-invalid="!!fieldError('postal_code')"
              />
              <small v-if="fieldError('postal_code')" class="field-error" role="alert">{{
                fieldError('postal_code')
              }}</small>
            </label>
          </div>
          <label>
            <span>{{ t('checkout.country') }}</span>
            <select
              v-model="form.country"
              autocomplete="country"
              :aria-invalid="!!fieldError('country')"
            >
              <option v-for="c in SHIPPING_COUNTRY_CODES" :key="c" :value="c">
                {{ t(`country.${c}` as MessageKey) }}
              </option>
            </select>
            <small v-if="fieldError('country')" class="field-error" role="alert">{{
              fieldError('country')
            }}</small>
          </label>
        </fieldset>

        <fieldset class="fields">
          <legend>{{ t('checkout.payment_method') }}</legend>
          <div class="radios">
            <label class="radio" :class="{ on: paymentMethod === 'gateway' }">
              <input v-model="paymentMethod" type="radio" name="pm" value="gateway" />
              <span class="radio__meta">
                <b>{{ t('checkout.pm_gateway') }}</b>
                <i>{{ t('checkout.pm_gateway_sub') }}</i>
              </span>
            </label>
            <label class="radio" :class="{ on: paymentMethod === 'cod' }">
              <input v-model="paymentMethod" type="radio" name="pm" value="cod" />
              <span class="radio__meta">
                <b>{{ t('checkout.pm_cod') }}</b>
                <i>{{ t('checkout.pm_cod_sub') }}</i>
              </span>
            </label>
          </div>
        </fieldset>

        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="act act--primary place" :disabled="placing" type="submit">
          {{ placing ? '…' : t('checkout.place') }}
        </button>
        <p class="fineprint">{{ t('checkout.fineprint_payment') }}</p>
      </form>
    </template>
  </main>
</template>

<style scoped>
.checkout {
  max-width: 600px;
  margin: 0 auto;
  padding: clamp(1.5rem, 4vw, 3rem) clamp(1rem, 4vw, 2.5rem) clamp(3rem, 6vw, 5rem);
}
.eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--accent-text);
}
.head {
  margin-bottom: 20px;
}
.head h1 {
  font-family: var(--font-display);
  font-size: clamp(1.35rem, 3vw, 1.8rem);
  font-weight: 800;
  margin-top: 4px;
}
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: clamp(1rem, 3.5vw, 1.75rem);
}

.lines {
  list-style: none;
  margin: 0 0 8px;
  padding: 0;
}
.line {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 0;
  border-bottom: 1px solid var(--border);
}
.line__img {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--photo-well);
  border: 1px solid var(--border);
  flex-shrink: 0;
  display: grid;
  place-items: center;
}
.line__img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
[data-theme='dark'] .line__img img {
  filter: brightness(0.88);
}
.line__ph {
  width: 100%;
  height: 100%;
  background: var(--surface-2);
}
.line__meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.line__meta b {
  font-size: 13px;
  font-weight: 600;
}
.line__meta i {
  font-style: normal;
  font-size: 11.5px;
  color: var(--text-subtle);
}
.line__price {
  font-size: 13px;
  font-weight: 700;
}
.total {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 16px;
  margin: 14px 0 4px;
}

.fields {
  border: 0;
  margin: 22px 0 0;
  padding: 0;
}
.fields legend {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text-subtle);
  margin-bottom: 12px;
}
.fields label:not(.radio) {
  display: block;
  margin-bottom: 13px;
}
.fields label:not(.radio) span {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 5px;
}
.fields label em {
  color: var(--text-subtle);
  font-style: normal;
  font-size: 11.5px;
}
.fields input,
.fields select {
  width: 100%;
  padding: 11px 13px;
  border: 1px solid var(--border-2);
  border-radius: var(--radius-sm);
  background: var(--bg);
  color: var(--text);
  font: inherit;
}
.fields input:focus,
.fields select:focus {
  outline: none;
  border-color: var(--accent);
}
.fields input[aria-invalid='true'],
.fields select[aria-invalid='true'] {
  border-color: var(--sale);
}
.fields__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.field-error {
  display: block;
  color: var(--sale);
  font-size: 12px;
  margin-top: 4px;
}

/* radio cards (saved address + payment method) */
.radios {
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.radio {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 12px 14px;
  border: 1px solid var(--border-2);
  border-radius: var(--radius-md);
  cursor: pointer;
}
.radio.on {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 6%, transparent);
}
.radio input {
  accent-color: var(--accent);
  width: 17px;
  height: 17px;
  margin-top: 2px;
  flex-shrink: 0;
}
.radio__meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.radio__meta b {
  font-size: 13.5px;
  font-weight: 700;
}
.radio__meta i {
  font-style: normal;
  font-size: 12px;
  color: var(--text-muted);
}
.dflt {
  font-style: normal;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--accent-text);
  margin-inline-start: 6px;
}

.error {
  color: var(--sale);
  font-size: 13px;
  margin-top: 14px;
}
.place {
  width: 100%;
  padding: 14px;
  margin-top: 16px;
}
.fineprint {
  font-size: 11.5px;
  color: var(--text-subtle);
  text-align: center;
  margin: 8px 0 0;
}

/* confirmation */
.confirm {
  text-align: center;
  padding-top: 12px;
}
.confirm__mark {
  width: 62px;
  height: 62px;
  margin: 0 auto 14px;
  border-radius: 999px;
  background: var(--success-bg);
  color: var(--success-fg);
  font-size: 28px;
  display: grid;
  place-items: center;
}
.confirm h1 {
  font-family: var(--font-display);
  font-size: clamp(1.4rem, 3vw, 1.9rem);
  font-weight: 800;
  margin: 2px 0 10px;
}
.confirm__line {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 15px;
}
.chip {
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font-size: 11.5px;
  font-weight: 700;
  text-transform: capitalize;
  background: var(--info-bg);
  color: var(--info-fg);
}
.chip--paid {
  background: var(--success-bg);
  color: var(--success-fg);
}
.breakdown {
  margin: 20px auto 14px;
  max-width: 320px;
  text-align: start;
}
.breakdown div {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13.5px;
}
.breakdown dt {
  color: var(--text-muted);
}
.breakdown dd {
  margin: 0;
}
.breakdown__total {
  border-top: 1px solid var(--border);
  font-weight: 700;
  font-size: 15px;
}
.confirm__note {
  font-size: 13px;
  color: var(--text-muted);
  margin: 3px 0;
}
.pay {
  margin: 20px 0;
}
.pay__done {
  color: var(--success-fg);
  font-weight: 700;
}
.pay__processing {
  color: var(--text-muted);
}
.pay__cod {
  background: var(--info-bg);
  color: var(--info-fg);
  border-radius: var(--radius-sm);
  padding: 11px 15px;
  font-size: 13.5px;
  display: inline-block;
}
.confirm__links {
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

.act {
  display: inline-block;
  padding: 12px 24px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-2);
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
}
.act--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--on-accent);
}
.act--primary:hover {
  opacity: 0.92;
}
.act:disabled {
  opacity: 0.6;
  cursor: default;
}
.state {
  text-align: center;
  padding: 48px 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: center;
}
</style>
