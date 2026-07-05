<script setup lang="ts">
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'
import { computed, onMounted, ref } from 'vue'
import { type Activity, type AdminProduct, type Order, api, formatPrice } from '../api'
import { currentLocale } from '../../lib/i18n'
import { type MessageKey, t } from '../locale'

const products = ref<AdminProduct[]>([])
const productTotal = ref(0)
const orders = ref<Order[]>([])
const activity = ref<Activity[]>([])
const canAudit = ref(true)
const loading = ref(true)

// ── headline metrics (all honest — derived from the real orders/products the API returns) ──
const visible = computed(() => products.value.filter((p) => p.is_visible).length)
const hidden = computed(() => Math.max(0, productTotal.value - visible.value))
const livePct = computed(() =>
  productTotal.value ? Math.round((visible.value / productTotal.value) * 100) : 0
)
const revenue = computed(() => orders.value.reduce((s, o) => s + o.total_cents, 0))
const avgOrder = computed(() => (orders.value.length ? revenue.value / orders.value.length : 0))
const awaiting = computed(
  () => orders.value.filter((o) => o.status === 'pending' || o.status === 'paid').length
)
const delivered = computed(() => orders.value.filter((o) => o.status === 'delivered').length)

// ── revenue-over-time: bucket orders by day over the selected range ──
const RANGES = [7, 30, 90] as const
const range = ref<(typeof RANGES)[number]>(30)
const DAY = 86_400_000

const series = computed(() => {
  const days = range.value
  const end = new Date()
  end.setHours(0, 0, 0, 0)
  const start = end.getTime() - (days - 1) * DAY
  const rev = Array(days).fill(0) as number[]
  const cnt = Array(days).fill(0) as number[]
  for (const o of orders.value) {
    if (!o.placed_at) continue
    const i = Math.floor((new Date(o.placed_at).setHours(0, 0, 0, 0) - start) / DAY)
    if (i >= 0 && i < days) {
      rev[i] += o.total_cents
      cnt[i] += 1
    }
  }
  return { rev, cnt }
})
const rangeRevenue = computed(() => series.value.rev.reduce((s, v) => s + v, 0))

// ── hero chart: two smooth series (revenue + orders), gradient-filled with peak markers ──
const CW = 620
const CH = 190
function smooth(pts: [number, number][]): string {
  if (pts.length === 0) return ''
  if (pts.length === 1) return `M${pts[0][0]},${pts[0][1]}`
  let d = `M${pts[0][0]},${pts[0][1]}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[i + 2] ?? p2
    const c1x = p1[0] + (p2[0] - p0[0]) / 6
    const c1y = p1[1] + (p2[1] - p0[1]) / 6
    const c2x = p2[0] - (p3[0] - p1[0]) / 6
    const c2y = p2[1] - (p3[1] - p1[1]) / 6
    d += ` C${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`
  }
  return d
}
function trace(vals: number[]) {
  const n = vals.length
  const max = Math.max(1, ...vals)
  const x = (i: number) => (n <= 1 ? 0 : (i / (n - 1)) * CW)
  const y = (v: number) => CH - 10 - (v / max) * (CH - 30)
  const pts = vals.map((v, i) => [x(i), y(v)] as [number, number])
  const line = smooth(pts)
  const area = line ? `${line} L${CW},${CH} L0,${CH} Z` : ''
  let mi = 0
  vals.forEach((v, i) => {
    if (v > vals[mi]) mi = i
  })
  return { line, area, mark: pts[mi] ?? [0, CH], hasData: vals.some((v) => v > 0) }
}
const chart = computed(() => ({
  rev: trace(series.value.rev),
  ord: trace(series.value.cnt),
  hasData: series.value.rev.some((v) => v > 0)
}))

// tiny 7-day bar sparkline for the gradient cards
function spark(vals: number[]): number[] {
  const max = Math.max(1, ...vals)
  return vals.slice(-7).map((v) => Math.max(8, Math.round((v / max) * 100)))
}
const revSpark = computed(() => spark(series.value.rev))
const ordWave = computed(() => {
  const vals = series.value.cnt.slice(-10)
  const max = Math.max(1, ...vals)
  const n = vals.length
  const pts = vals.map(
    (v, i) => [(n <= 1 ? 0 : (i / (n - 1)) * 100), 30 - (v / max) * 24 - 3] as [number, number]
  )
  const line = smooth(pts)
  return { line, area: line ? `${line} L100,34 L0,34 Z` : '' }
})

// ── order-status donut ──
const STATUS_ORDER = ['paid', 'pending', 'shipped', 'delivered', 'cancelled'] as const
// reuse the vibrant KPI-card palette (pink/violet/blue/orange) + one teal for the 5th status
const STATUS_TONE: Record<string, string> = {
  paid: '--c-blue',
  pending: '--c-orange',
  shipped: '--c-violet',
  delivered: '--c-teal',
  cancelled: '--c-pink'
}
const breakdown = computed(() => {
  const counts: Record<string, number> = {}
  for (const o of orders.value) counts[o.status] = (counts[o.status] ?? 0) + 1
  const total = orders.value.length || 1
  return STATUS_ORDER.filter((s) => counts[s]).map((s) => ({
    status: s,
    count: counts[s],
    pct: Math.round((counts[s] / total) * 100),
    frac: counts[s] / total,
    tone: STATUS_TONE[s]
  }))
})
const R = 54
const C = 2 * Math.PI * R
const donut = computed(() => {
  let start = 0
  return breakdown.value.map((s) => {
    const dash = s.frac * C
    const seg = { ...s, dash, offset: -start }
    start += dash
    return seg
  })
})

// ── vibrant gradient KPI cards (the reference's palette, per design direction) ──
const kpis = computed(() => [
  {
    key: 'rev',
    tone: 'pink',
    label: t('dash.revenue'),
    value: formatPrice(revenue.value),
    sub: t('dash.kpi_last_range', { d: range.value, v: formatPrice(rangeRevenue.value) }),
    kind: 'bars' as const
  },
  {
    key: 'ord',
    tone: 'violet',
    label: t('nav.orders'),
    value: String(orders.value.length),
    sub: t('dash.awaiting', { n: awaiting.value }),
    kind: 'wave' as const
  },
  {
    key: 'prod',
    tone: 'blue',
    label: t('nav.products'),
    value: String(productTotal.value),
    sub: t('dash.kpi_hidden', { n: hidden.value }),
    kind: 'meter' as const,
    bar: productTotal.value ? visible.value / productTotal.value : 0
  },
  {
    key: 'live',
    tone: 'orange',
    label: t('dash.live'),
    value: String(visible.value),
    sub: t('dash.kpi_live_pct', { n: livePct.value }),
    kind: 'meter' as const,
    bar: productTotal.value ? visible.value / productTotal.value : 0
  }
])

// ── stat chips under the hero ──
const chips = computed(() => [
  { icon: 'pi-chart-line', tone: 'a', label: t('dash.chip_avg'), value: formatPrice(avgOrder.value) },
  { icon: 'pi-clock', tone: 'b', label: t('dash.chip_awaiting'), value: String(awaiting.value) },
  { icon: 'pi-check-circle', tone: 'c', label: t('dash.chip_delivered'), value: String(delivered.value) },
  { icon: 'pi-eye', tone: 'd', label: t('dash.live'), value: `${visible.value}` }
])

// ── activity timeline: colored circular icons ──
const ACT_STYLE = [
  { tone: 'pink', icon: 'pi-bolt' },
  { tone: 'violet', icon: 'pi-pencil' },
  { tone: 'blue', icon: 'pi-tag' },
  { tone: 'orange', icon: 'pi-refresh' },
  { tone: 'a', icon: 'pi-box' },
  { tone: 'c', icon: 'pi-user-plus' }
]
const feed = computed(() =>
  activity.value.slice(0, 6).map((a, i) => ({ ...a, ...ACT_STYLE[i % ACT_STYLE.length] }))
)

const severity: Record<string, string> = {
  pending: 'secondary',
  paid: 'info',
  shipped: 'warn',
  delivered: 'success',
  cancelled: 'danger'
}

function when(iso: string | null): string {
  return iso
    ? new Date(iso).toLocaleString(currentLocale(), {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    : '—'
}

onMounted(async () => {
  try {
    const page = await api.products()
    products.value = page.data
    productTotal.value = page.total
  } catch {
    /* no catalog access */
  }
  try {
    orders.value = await api.orders()
  } catch {
    /* no orders access */
  }
  try {
    activity.value = await api.audit()
  } catch {
    canAudit.value = false
  }
  loading.value = false
})
</script>

<template>
  <section class="dash">
    <header class="page">
      <div>
        <p class="eyebrow">{{ t('dash.eyebrow') }}</p>
        <h1>{{ t('nav.dashboard') }}</h1>
        <p class="page__sub">{{ t('dash.sub') }}</p>
      </div>
      <RouterLink class="cta" to="/admin/products"
        ><i class="pi pi-box" /> {{ t('dash.manage_products') }}</RouterLink
      >
    </header>

    <div class="top">
      <!-- HERO: revenue + two-series trend -->
      <section class="panel hero">
        <div class="hero__head">
          <div>
            <p class="hero__eye">{{ t('dash.revenue') }}</p>
            <div class="hero__val">{{ loading ? '—' : formatPrice(revenue) }}</div>
            <p class="hero__meta">
              {{ t('dash.hero_meta', { orders: orders.length, avg: formatPrice(avgOrder) }) }}
            </p>
          </div>
          <div class="hero__tools">
            <div class="chartkey">
              <span class="chartkey__i"><i class="d d--rev" />{{ t('dash.revenue') }}</span>
              <span class="chartkey__i"><i class="d d--ord" />{{ t('nav.orders') }}</span>
            </div>
            <div class="range" role="group" :aria-label="t('dash.range')">
              <button
                v-for="r in RANGES"
                :key="r"
                class="range__opt"
                :class="{ on: range === r }"
                @click="range = r"
              >
                {{ t('dash.range_days', { d: r }) }}
              </button>
            </div>
          </div>
        </div>

        <div class="chart">
          <svg class="chart__svg" viewBox="0 0 620 190" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <linearGradient id="gRev" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stop-color="var(--accent)" stop-opacity="0.30" />
                <stop offset="1" stop-color="var(--accent)" stop-opacity="0" />
              </linearGradient>
              <linearGradient id="gOrd" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stop-color="#7b5cff" stop-opacity="0.22" />
                <stop offset="1" stop-color="#7b5cff" stop-opacity="0" />
              </linearGradient>
            </defs>
            <path :d="chart.ord.area" fill="url(#gOrd)" />
            <path :d="chart.rev.area" fill="url(#gRev)" />
            <path
              :d="chart.ord.line"
              fill="none"
              stroke="#7b5cff"
              stroke-width="2"
              stroke-linejoin="round"
              stroke-linecap="round"
              vector-effect="non-scaling-stroke"
            />
            <path
              :d="chart.rev.line"
              fill="none"
              stroke="var(--accent)"
              stroke-width="2.5"
              stroke-linejoin="round"
              stroke-linecap="round"
              vector-effect="non-scaling-stroke"
            />
          </svg>
          <!-- peak markers, positioned in % so they don't stretch with the svg -->
          <template v-if="chart.hasData">
            <span
              class="dot dot--rev"
              :style="{ left: `${(chart.rev.mark[0] / CW) * 100}%`, top: `${(chart.rev.mark[1] / CH) * 100}%` }"
            />
            <span
              class="dot dot--ord"
              :style="{ left: `${(chart.ord.mark[0] / CW) * 100}%`, top: `${(chart.ord.mark[1] / CH) * 100}%` }"
            />
          </template>
          <p v-if="!loading && !chart.hasData" class="chart__empty">
            {{ t('dash.no_revenue_range') }}
          </p>
        </div>

        <div class="chips">
          <div v-for="c in chips" :key="c.label" class="chip">
            <span class="chip__icn" :class="`t-${c.tone}`"><i :class="`pi ${c.icon}`" /></span>
            <span class="chip__meta">
              <span class="chip__label">{{ c.label }}</span>
              <span class="chip__val">{{ loading ? '—' : c.value }}</span>
            </span>
          </div>
        </div>
      </section>

      <!-- DONUT: orders by status -->
      <section class="panel donutp">
        <div class="panel__head">
          <h2>{{ t('dash.by_status') }}</h2>
          <RouterLink class="link" to="/admin/orders"
            >{{ t('common.view_all') }} {{ t('common.fwd') }}</RouterLink
          >
        </div>
        <div v-if="orders.length" class="donut">
          <svg class="donut__svg" viewBox="0 0 140 140">
            <g transform="rotate(-90 70 70)">
              <circle class="donut__track" cx="70" cy="70" :r="R" />
              <circle
                v-for="s in donut"
                :key="s.status"
                cx="70"
                cy="70"
                :r="R"
                class="donut__seg"
                :stroke="`var(${s.tone})`"
                :stroke-dasharray="`${s.dash} ${C}`"
                :stroke-dashoffset="s.offset"
              />
            </g>
          </svg>
          <div class="donut__c">
            <b>{{ orders.length }}</b>
            <span>{{ t('nav.orders') }}</span>
          </div>
        </div>
        <p v-else class="empty">{{ t('orders.none') }}</p>
        <ul v-if="orders.length" class="legend">
          <li v-for="s in breakdown" :key="s.status">
            <span class="legend__dot" :style="{ background: `var(${s.tone})` }" />
            <span class="legend__lbl">{{ t(`order.${s.status}` as MessageKey) }}</span>
            <span class="legend__pct">{{ s.pct }}%</span>
            <span class="legend__n">{{ s.count }}</span>
          </li>
        </ul>
      </section>
    </div>

    <!-- gradient KPI cards -->
    <div class="kpis">
      <article v-for="k in kpis" :key="k.key" class="kpi" :class="`kpi--${k.tone}`">
        <span class="kpi__label">{{ k.label }}</span>
        <span class="kpi__val">{{ loading ? '—' : k.value }}</span>
        <span class="kpi__sub">{{ loading ? ' ' : k.sub }}</span>
        <div v-if="k.kind === 'bars'" class="kpi__spark">
          <span v-for="(h, i) in revSpark" :key="i" class="kpi__bar" :style="{ height: `${h}%` }" />
        </div>
        <svg v-else-if="k.kind === 'wave'" class="kpi__wave" viewBox="0 0 100 34" preserveAspectRatio="none">
          <path :d="ordWave.area" fill="rgba(255,255,255,0.25)" />
          <path :d="ordWave.line" fill="none" stroke="#fff" stroke-width="2" vector-effect="non-scaling-stroke" />
        </svg>
        <div v-else class="kpi__meter"><span :style="{ width: `${Math.round((k.bar ?? 0) * 100)}%` }" /></div>
      </article>
    </div>

    <div class="row2">
      <div class="panel">
        <div class="panel__head">
          <h2>{{ t('dash.recent_orders') }}</h2>
          <RouterLink class="link" to="/admin/orders"
            >{{ t('common.view_all') }} {{ t('common.fwd') }}</RouterLink
          >
        </div>
        <DataTable
          :value="orders.slice(0, 8)"
          :loading="loading"
          size="small"
          data-key="id"
          class="tbl"
        >
          <template #empty
            ><p class="empty">{{ t('orders.none') }}</p></template
          >
          <Column :header="t('orders.order')">
            <template #body="{ data }"
              ><span class="mono">#{{ data.id }}</span></template
            >
          </Column>
          <Column :header="t('orders.items')">
            <template #body="{ data }">{{ data.items.length }}</template>
          </Column>
          <Column :header="t('common.status')">
            <template #body="{ data }">
              <Tag
                :value="t(`order.${data.status}` as MessageKey)"
                :severity="severity[data.status] ?? 'secondary'"
              />
            </template>
          </Column>
          <Column :header="t('common.total')" class="ta-r">
            <template #body="{ data }"
              ><span class="mono">{{ formatPrice(data.total_cents) }}</span></template
            >
          </Column>
        </DataTable>
        <p v-if="orders.length" class="showing">
          {{ t('dash.showing', { n: Math.min(8, orders.length), total: orders.length }) }}
        </p>
      </div>

      <div class="panel">
        <div class="panel__head">
          <h2>{{ t('dash.recent_activity') }}</h2>
          <RouterLink v-if="canAudit" class="link" to="/admin/audit"
            >{{ t('common.view_all') }} {{ t('common.fwd') }}</RouterLink
          >
        </div>
        <p v-if="!canAudit" class="empty">{{ t('dash.no_audit') }}</p>
        <p v-else-if="!loading && !activity.length" class="empty">
          {{ t('audit.none') }}
        </p>
        <ul v-else class="feed">
          <li v-for="a in feed" :key="a.id" class="feed__row">
            <span class="feed__icn" :class="`t-${a.tone}`"><i :class="`pi ${a.icon}`" /></span>
            <span class="feed__desc">{{ a.description }}</span>
            <span class="feed__time">{{ when(a.created_at) }}</span>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* vibrant card palette — matches the analytics reference, per design direction */
.dash {
  --g-pink: linear-gradient(135deg, #f2618f, #c0206a);
  --g-violet: linear-gradient(135deg, #8b62f0, #5b3fd6);
  --g-blue: linear-gradient(135deg, #3fb9e6, #2a86d6);
  --g-orange: linear-gradient(135deg, #fbab3c, #f47b20);
  --c-pink: #d83b7c;
  --c-violet: #6f4fe0;
  --c-blue: #2f9fd8;
  --c-orange: #f2871f;
  --c-teal: #16b8a6; /* 5th hue so order-status segments extend the KPI palette */
}
.eyebrow {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--accent);
  font-weight: 600;
}
.page {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}
.page h1 {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 6px 0 2px;
}
.page__sub {
  color: var(--text-muted);
  font-size: 13px;
  margin: 0;
}
.cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 16px;
  border-radius: var(--radius-md);
  background: var(--accent);
  color: var(--on-accent);
  font-weight: 600;
  font-size: 14px;
  text-decoration: none;
}

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-1);
  padding: 20px;
}
.panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.panel__head h2 {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
}
.link {
  font-size: 12.5px;
  color: var(--accent);
  text-decoration: none;
  font-weight: 600;
  white-space: nowrap;
}

/* ── top row: hero + donut ── */
.top {
  display: grid;
  grid-template-columns: 1.7fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.hero__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.hero__eye {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--text-subtle);
  font-weight: 600;
  margin: 0;
}
.hero__val {
  font-family: var(--font-display);
  font-size: clamp(30px, 4vw, 42px);
  font-weight: 800;
  letter-spacing: -0.02em;
  margin: 4px 0 2px;
}
.hero__meta {
  color: var(--text-muted);
  font-size: 12.5px;
  margin: 0;
}
.hero__tools {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}
.chartkey {
  display: flex;
  gap: 14px;
}
.chartkey__i {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}
.d {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}
.d--rev {
  background: var(--accent);
}
.d--ord {
  background: #7b5cff;
}
.range {
  display: inline-flex;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 3px;
  gap: 2px;
  flex: none;
}
.range__opt {
  border: 0;
  background: none;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  padding: 5px 10px;
  border-radius: calc(var(--radius-md) - 3px);
  cursor: pointer;
}
.range__opt.on {
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow-1);
}
.chart {
  position: relative;
  margin: 18px 0 6px;
}
.chart__svg {
  display: block;
  width: 100%;
  height: 180px;
}
.dot {
  position: absolute;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  border: 3px solid var(--surface);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
}
.dot--rev {
  background: var(--accent);
}
.dot--ord {
  background: #7b5cff;
}
.chart__empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--text-subtle);
  font-size: 13px;
  margin: 0;
}
.chips {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  border-top: 1px solid var(--border);
  padding-top: 16px;
  margin-top: 8px;
}
.chip {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.chip__icn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 15px;
  flex: none;
}
.chip__meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chip__label {
  font-size: 11px;
  color: var(--text-subtle);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.chip__val {
  font-weight: 700;
  font-size: 14px;
}
.t-a {
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
}
.t-b {
  background: var(--info-bg);
  color: var(--info-fg);
}
.t-c {
  background: var(--success-bg);
  color: var(--success-fg);
}
.t-d {
  background: var(--warn-bg);
  color: var(--warn-fg);
}
.t-pink {
  background: var(--g-pink);
  color: #fff;
}
.t-violet {
  background: var(--g-violet);
  color: #fff;
}
.t-blue {
  background: var(--g-blue);
  color: #fff;
}
.t-orange {
  background: var(--g-orange);
  color: #fff;
}

/* ── donut ── */
.donutp {
  display: flex;
  flex-direction: column;
}
.donut {
  position: relative;
  width: 158px;
  height: 158px;
  margin: 6px auto 16px;
}
.donut__svg {
  width: 100%;
  height: 100%;
}
.donut__track {
  fill: none;
  stroke: var(--surface-2);
  stroke-width: 16;
}
.donut__seg {
  fill: none;
  stroke-width: 16;
  stroke-linecap: butt;
}
.donut__c {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  text-align: center;
}
.donut__c b {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
}
.donut__c span {
  font-size: 11px;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.legend {
  list-style: none;
  margin: auto 0 0;
  padding: 0;
  display: grid;
  gap: 10px;
}
.legend li {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}
.legend__dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}
.legend__lbl {
  color: var(--text-muted);
}
.legend__pct {
  color: var(--text-subtle);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}
.legend__n {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  min-width: 16px;
  text-align: end;
}

/* ── gradient KPI cards ── */
.kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.kpi {
  position: relative;
  border-radius: var(--radius-lg);
  padding: 18px 18px 16px;
  color: #fff;
  overflow: hidden;
  min-height: 132px;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-1);
}
.kpi--pink {
  background: var(--g-pink);
}
.kpi--violet {
  background: var(--g-violet);
}
.kpi--blue {
  background: var(--g-blue);
}
.kpi--orange {
  background: var(--g-orange);
}
.kpi__label {
  font-size: 12px;
  font-weight: 600;
  opacity: 0.9;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.kpi__val {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 30px;
  letter-spacing: -0.02em;
  margin-top: 8px;
}
.kpi__sub {
  font-size: 11.5px;
  opacity: 0.9;
  margin-top: 2px;
}
.kpi__spark {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 30px;
  margin-top: auto;
  padding-top: 10px;
}
.kpi__bar {
  flex: 1;
  background: rgba(255, 255, 255, 0.55);
  border-radius: 3px 3px 0 0;
  min-height: 4px;
}
.kpi__wave {
  width: 100%;
  height: 34px;
  margin-top: auto;
}
.kpi__meter {
  height: 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.3);
  margin-top: auto;
  overflow: hidden;
}
.kpi__meter span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: #fff;
}

/* ── bottom row ── */
.row2 {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 16px;
}
.empty {
  color: var(--text-subtle);
  text-align: center;
  padding: 28px 0;
  margin: 0;
  font-size: 14px;
}
.mono {
  font-family: var(--font-mono);
  font-size: 12.5px;
}
.tbl :deep(.p-datatable-table-container) {
  overflow-x: auto;
}
.tbl :deep(.p-datatable-thead > tr > th) {
  background: var(--side-bg);
  color: var(--side-text-hi, #fff);
  border-color: transparent;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.tbl :deep(.p-datatable-thead > tr > th:first-child) {
  border-start-start-radius: var(--radius-md);
}
.tbl :deep(.p-datatable-thead > tr > th:last-child) {
  border-start-end-radius: var(--radius-md);
}
.tbl :deep(.ta-r) {
  text-align: end;
}
.showing {
  color: var(--text-subtle);
  font-size: 12px;
  margin: 12px 2px 0;
}
.feed {
  list-style: none;
  margin: 0;
  padding: 4px 0;
}
.feed__row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 11px 0;
  border-top: 1px solid var(--border);
}
.feed__row:first-child {
  border-top: 0;
}
.feed__icn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 15px;
  flex: none;
}
.feed__desc {
  font-size: 13px;
}
.feed__time {
  color: var(--text-subtle);
  font-size: 11.5px;
  white-space: nowrap;
}

@media (max-width: 1000px) {
  .top {
    grid-template-columns: 1fr;
  }
  .row2 {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .page {
    flex-direction: column;
    gap: 14px;
  }
  .page h1 {
    font-size: 23px;
  }
  .cta {
    align-self: stretch;
    justify-content: center;
  }
  .kpis {
    grid-template-columns: repeat(2, 1fr);
  }
  .chips {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px 10px;
  }
  .hero__head {
    flex-direction: column;
  }
  .hero__tools {
    align-items: flex-start;
    flex-direction: row;
    width: 100%;
    justify-content: space-between;
  }
}
</style>
