<script setup lang="ts">
// Cancelled is a terminal branch: the timeline collapses to placed → cancelled, skipping the rest.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { type Order, api, formatPrice, orderTokens } from '../api'
import { type MessageKey, t } from '../locale'
import { pageTitle } from '../pageTitle'

const route = useRoute()
const orderId = Number(route.params.id)
const token = orderTokens.get(orderId) // guests hold the receipt; signed-in owners use bearer

// slim mobile header title
pageTitle.value = `${t('order.eyebrow')} #${orderId}`
onBeforeUnmount(() => (pageTitle.value = ''))

const order = ref<Order | null>(null)
const loading = ref(true)
const failed = ref(false)
const acting = ref(false)
const actionError = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const cancellable = computed(
  () => order.value !== null && ['pending', 'paid'].includes(order.value.status)
)
// K15: a paid cancel is a refund, not a bare cancel — the confirm copy + button label say so
const isPaidCancel = computed(() => order.value?.status === 'paid')
const payable = computed(
  () => order.value?.status === 'pending' && order.value.payment_method === 'gateway'
)

const steps = computed(() => order.value?.timeline ?? [])
const doneCount = computed(() => steps.value.filter((s) => s.at !== null).length)

function stepLabel(status: string): string {
  return t(`order.step_${status}` as MessageKey)
}
function stepTime(at: string | null): string {
  return at ? new Date(at).toLocaleString() : ''
}

function stopPolling() {
  if (pollTimer !== null) clearInterval(pollTimer)
  pollTimer = null
}

async function load() {
  loading.value = true
  failed.value = false
  try {
    order.value = await api.order(orderId, token)
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

async function payNow() {
  if (!order.value) return
  acting.value = true
  actionError.value = null
  try {
    await api.pay(orderId, token)
    let attempts = 0
    stopPolling()
    pollTimer = setInterval(async () => {
      attempts += 1
      const fresh = await api.order(orderId, token)
      order.value = fresh
      if (fresh.status === 'paid' || fresh.payment_status === 'failed' || attempts >= 20) {
        if (fresh.payment_status === 'failed' && fresh.status !== 'paid') {
          actionError.value = t('checkout.pay_failed')
        }
        acting.value = false
        stopPolling()
      }
    }, 1000)
  } catch {
    acting.value = false
    actionError.value = t('checkout.pay_start_error')
  }
}

async function cancelOrder() {
  if (!order.value) return
  const confirmMsg = isPaidCancel.value
    ? t('order.cancel_refund_confirm', { n: orderId })
    : t('order.cancel_confirm', { n: orderId })
  if (!window.confirm(confirmMsg)) return
  acting.value = true
  actionError.value = null
  try {
    // same endpoint either way — a paid order routes server-side to a refund (DR-0065)
    order.value = await api.cancelOrder(orderId, token)
  } catch {
    actionError.value = isPaidCancel.value ? t('order.refund_error') : t('order.cancel_error')
  } finally {
    acting.value = false
  }
}

function openInvoice() {
  if (!order.value) return
  window.open(api.invoiceUrl(order.value.id, token ?? order.value.token), '_blank', 'noopener')
}

onMounted(load)
onBeforeUnmount(stopPolling)
</script>

<template>
  <main class="detail">
    <p v-if="loading" class="muted center">{{ t('common.loading') }}</p>

    <div v-else-if="failed || !order" class="state">
      <h1>{{ t('order.not_found') }}</h1>
      <p class="muted">{{ t('order.not_found_note') }}</p>
      <RouterLink class="act act--primary" to="/account">{{ t('order.back_account') }}</RouterLink>
    </div>

    <template v-else>
      <header class="head">
        <p class="eyebrow">{{ t('order.eyebrow') }}</p>
        <h1>
          {{ t('checkout.order') }} #{{ order.id }}
          <span class="chip" :class="`chip--${order.status}`">{{
            t(`order.${order.status}` as MessageKey)
          }}</span>
        </h1>
        <p v-if="order.payment_status === 'failed' && order.status === 'pending'" class="muted">
          {{ t('order.last_payment_failed') }}
        </p>
      </header>

      <!-- tracking stepper -->
      <section v-if="steps.length" class="panel">
        <h2>{{ t('order.track_title') }}</h2>
        <ol class="track">
          <li
            v-for="(s, i) in steps"
            :key="s.status"
            class="step"
            :class="{
              'step--done': s.at !== null,
              'step--current': s.at !== null && i === doneCount - 1,
              'step--cancelled': s.status === 'cancelled',
              'step--refund': s.status === 'refunded' || s.status === 'refund_pending'
            }"
          >
            <span class="step__dot" aria-hidden="true">
              <svg
                v-if="
                  s.at !== null &&
                  s.status !== 'cancelled' &&
                  s.status !== 'refunded' &&
                  s.status !== 'refund_pending'
                "
                viewBox="0 0 24 24"
              >
                <path d="M5 12l5 5 9-10" />
              </svg>
              <svg v-else-if="s.status === 'cancelled'" viewBox="0 0 24 24">
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
              <!-- refunded: a return arrow; refund_pending: no glyph, the info dot reads as in-flight -->
              <svg v-else-if="s.status === 'refunded'" viewBox="0 0 24 24">
                <path d="M9 7H5v4M5 7a9 9 0 1 1-2 6" />
              </svg>
            </span>
            <span class="step__meta">
              <b>{{ stepLabel(s.status) }}</b>
              <i v-if="s.at">{{ stepTime(s.at) }}</i>
            </span>
          </li>
        </ol>
      </section>

      <section class="panel">
        <h2>{{ t('order.items') }}</h2>
        <ul class="lines">
          <li v-for="line in order.items" :key="line.product_variant_id" class="line">
            <component
              :is="line.product_slug ? 'RouterLink' : 'span'"
              :to="line.product_slug ? `/products/${line.product_slug}` : undefined"
              class="line__img"
            >
              <img v-if="line.image_url" :src="line.image_url" :alt="line.product_name" />
              <span v-else class="line__ph" aria-hidden="true" />
            </component>
            <span class="line__meta">
              <RouterLink
                v-if="line.product_slug"
                class="line__name"
                :to="`/products/${line.product_slug}`"
                >{{ line.product_name }}</RouterLink
              >
              <b v-else>{{ line.product_name }}</b>
              <i>{{ line.variant_name }} · ×{{ line.quantity }}</i>
            </span>
            <span class="line__price tnum">{{
              formatPrice(line.unit_price_cents * line.quantity)
            }}</span>
          </li>
        </ul>
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
        <p class="method">
          <span class="method__label">{{ t('account.order_method') }}:</span>
          {{ t(`pay.${order.payment_method}` as MessageKey) }}
        </p>
      </section>

      <section class="panel">
        <h2>{{ t('order.delivery') }}</h2>
        <address class="address">
          {{ order.address.name }}<br />
          {{ order.address.line1
          }}<span v-if="order.address.line2"><br />{{ order.address.line2 }}</span
          ><br />
          {{ order.address.city }}, {{ order.address.postal_code }}
          {{ order.address.country }}
        </address>
        <p class="muted">
          {{ t('order.updates_to', { email: order.contact_email }) }}
        </p>
        <p v-if="order.tracking_number" class="muted">
          {{ t('order.tracking', { number: order.tracking_number }) }}
        </p>
      </section>

      <section class="actions" aria-live="polite">
        <p v-if="actionError" class="error" role="alert">{{ actionError }}</p>
        <button v-if="payable" class="act act--primary" :disabled="acting" @click="payNow">
          {{
            acting
              ? t('checkout.processing_short')
              : t('checkout.pay_now', { total: formatPrice(order.total_cents) })
          }}
        </button>
        <button class="act" @click="openInvoice">
          {{ t('account.order_invoice') }}
        </button>
        <button v-if="cancellable" class="act act--danger" :disabled="acting" @click="cancelOrder">
          {{ isPaidCancel ? t('order.cancel_and_refund') : t('order.cancel') }}
        </button>
        <p v-if="order.status === 'cancelled'" class="muted">
          {{ t('order.cancelled_note') }}
        </p>
        <p v-if="order.status === 'refunded' && order.refund" class="muted">
          {{ t('order.refunded_note', { amount: formatPrice(order.refund.amount_cents) }) }}
        </p>
      </section>
    </template>
  </main>
</template>

<style scoped>
.detail {
  max-width: 720px;
  margin: 0 auto;
  padding: clamp(1.5rem, 4vw, 3rem) clamp(1rem, 4vw, 2.5rem) clamp(3rem, 6vw, 5rem);
}
.center {
  text-align: center;
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
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.chip {
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font-family: var(--font-text);
  font-size: 11.5px;
  font-weight: 700;
  text-transform: capitalize;
  background: var(--info-bg);
  color: var(--info-fg);
}
.chip--paid,
.chip--delivered,
.chip--refunded {
  background: var(--success-bg);
  color: var(--success-fg);
}
.chip--cancelled {
  background: var(--danger-bg);
  color: var(--danger-fg);
}
.chip--shipped {
  background: var(--warn-bg);
  color: var(--warn-fg);
}
/* .chip--refund_pending is the base .chip color (--info-bg/--info-fg) already — explicit rule so
   the mapping is documented, not just an accident of the default (K15). */
.chip--refund_pending {
  background: var(--info-bg);
  color: var(--info-fg);
}

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: clamp(1rem, 3vw, 1.5rem);
  margin-bottom: 14px;
}
.panel h2 {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-subtle);
  margin-bottom: 16px;
}

/* stepper — vertical on phones, horizontal >=640px */
.track {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
  counter-reset: step;
}
.step {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding-bottom: 22px;
}
.step:last-child {
  padding-bottom: 0;
}
.step::before {
  content: '';
  position: absolute;
  inset-inline-start: 13px;
  top: 28px;
  bottom: 0;
  width: 2px;
  background: var(--border-2);
}
.step:last-child::before {
  display: none;
}
.step--done::before {
  background: var(--accent);
}
.step__dot {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  border: 2px solid var(--border-2);
  background: var(--surface);
  display: grid;
  place-items: center;
  flex-shrink: 0;
  z-index: 1;
}
.step__dot svg {
  width: 14px;
  height: 14px;
  stroke: currentColor;
  fill: none;
  stroke-width: 2.4;
}
.step--done .step__dot {
  border-color: var(--accent);
  background: var(--accent);
  color: var(--on-accent);
}
.step--cancelled .step__dot {
  border-color: var(--sale);
  background: var(--danger-bg);
  color: var(--danger-fg);
}
/* refunded / refund-in-progress: a neutral money-returned state, not a green success step —
   mirrors the .chip--refund_pending info treatment. After .step--done so it wins the dot color. */
.step--refund .step__dot {
  border-color: var(--info-fg);
  background: var(--info-bg);
  color: var(--info-fg);
}
.step__meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-top: 3px;
}
.step__meta b {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text-subtle);
}
.step--done .step__meta b {
  color: var(--text);
}
.step--cancelled .step__meta b {
  color: var(--danger-fg);
}
.step--refund .step__meta b {
  color: var(--info-fg);
}
.step__meta i {
  font-style: normal;
  font-size: 11.5px;
  color: var(--text-subtle);
}

@media (min-width: 640px) {
  .track {
    flex-direction: row;
  }
  .step {
    flex: 1;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 8px;
    padding-bottom: 0;
  }
  .step::before {
    inset-inline-start: 50%;
    top: 13px;
    bottom: auto;
    width: 100%;
    height: 2px;
  }
  .step__meta {
    padding-top: 0;
  }
}

/* lines */
.lines {
  list-style: none;
  margin: 0;
  padding: 0;
}
.line {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.line__img {
  width: 48px;
  height: 48px;
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
.line__meta b,
.line__name {
  font-size: 13.5px;
  font-weight: 600;
}
.line__name {
  color: var(--text);
  text-decoration: none;
}
.line__name:hover {
  color: var(--accent-text);
}
.line__meta i {
  font-style: normal;
  font-size: 12px;
  color: var(--text-subtle);
}
.line__price {
  font-size: 13.5px;
  font-weight: 700;
}

.breakdown {
  margin: 14px 0 0;
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
  margin-top: 4px;
  padding-top: 10px;
}
.method {
  margin-top: 12px;
  font-size: 13px;
}
.method__label {
  color: var(--text-subtle);
}

.address {
  font-style: normal;
  line-height: 1.6;
  margin-bottom: 8px;
  font-size: 14px;
}
.muted {
  color: var(--text-subtle);
  font-size: 13px;
}
.error {
  width: 100%;
  color: var(--sale);
  font-size: 13px;
}
.state {
  text-align: center;
  padding: 64px 0;
}
.state h1 {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 800;
  margin-bottom: 8px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.act {
  padding: 11px 22px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-2);
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
}
.act:hover {
  border-color: var(--accent);
  color: var(--accent-text);
}
.act--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--on-accent);
}
.act--primary:hover {
  color: var(--on-accent);
  opacity: 0.92;
}
.act--danger {
  color: var(--sale);
}
.act--danger:hover {
  border-color: var(--sale);
  color: var(--sale);
}
.act:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
