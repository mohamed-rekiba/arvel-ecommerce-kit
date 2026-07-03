<script setup lang="ts">
// Wishlist (profile ref 2): a table on desktop / cards on mobile — thumb, price, stock,
// add-to-cart + remove per row, plus add-all and clear. Adding picks the first in-stock
// variant (the card's own quick-add rule).
import { computed, ref } from "vue";
import { type Product, api, formatPrice } from "../../api";
import { useCart } from "../../cart";
import { useWishlist } from "../../wishlist";
import { t } from "../../locale";

const wishlist = useWishlist();
const cart = useCart();
const busy = ref<number | null>(null);
const bulkBusy = ref(false);
const msg = ref<string | null>(null);

const rows = computed(() => wishlist.state.products);

function firstVariant(p: Product) {
  return (p.variants ?? []).find((v) => v.stock > 0) ?? null;
}
const inStock = (p: Product) => firstVariant(p) !== null;
function unitPrice(p: Product): number {
  return p.deal ? p.deal.deal_price_cents : p.price_cents;
}

async function addOne(p: Product) {
  const variant = firstVariant(p);
  if (!variant) return;
  busy.value = p.id;
  msg.value = null;
  try {
    await cart.add(variant.id, 1);
    msg.value = t("account.wl_added");
  } finally {
    busy.value = null;
  }
}

async function addAll() {
  bulkBusy.value = true;
  msg.value = null;
  try {
    for (const p of rows.value) {
      const variant = firstVariant(p);
      if (variant) await cart.add(variant.id, 1);
    }
    msg.value = t("account.wl_added");
  } finally {
    bulkBusy.value = false;
  }
}

async function removeOne(p: Product) {
  await wishlist.toggle(p.id);
}

async function clearAll() {
  if (!window.confirm(t("account.wl_clear_confirm"))) return;
  bulkBusy.value = true;
  try {
    for (const p of [...rows.value]) await wishlist.toggle(p.id);
  } finally {
    bulkBusy.value = false;
  }
}
</script>

<template>
  <div class="card">
    <div class="head">
      <h2 class="card__title">{{ t("account.menu_wishlist") }}</h2>
      <div v-if="rows.length" class="head__actions">
        <button class="cta cta--sm" :disabled="bulkBusy" @click="addAll">{{ t("account.wl_add_all") }}</button>
        <button class="ghost" :disabled="bulkBusy" @click="clearAll">{{ t("account.wl_clear") }}</button>
      </div>
    </div>
    <p v-if="msg" class="notice" role="status">{{ msg }}</p>
    <p v-if="!rows.length" class="muted">{{ t("account.wl_empty") }}</p>

    <!-- desktop table -->
    <div v-if="rows.length" class="tablewrap">
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ t("account.wl_product") }}</th>
            <th>{{ t("account.wl_price") }}</th>
            <th>{{ t("account.wl_stock") }}</th>
            <th>{{ t("account.wl_action") }}</th>
            <th><span class="sr">{{ t("account.wl_remove") }}</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in rows" :key="p.id">
            <td>
              <RouterLink class="prod" :to="`/products/${p.slug}`">
                <span class="prod__img">
                  <img v-if="p.gallery[0]" :src="p.gallery[0].thumb_url" alt="" />
                  <span v-else class="prod__ph" aria-hidden="true" />
                </span>
                <b>{{ p.translation.name }}</b>
              </RouterLink>
            </td>
            <td class="tnum">{{ formatPrice(unitPrice(p)) }}</td>
            <td>
              <span class="stock" :class="inStock(p) ? 'stock--in' : 'stock--out'">
                {{ inStock(p) ? t("account.wl_in_stock") : t("account.wl_out_stock") }}
              </span>
            </td>
            <td>
              <button class="cta cta--sm" :disabled="!inStock(p) || busy === p.id" @click="addOne(p)">
                {{ t("account.wl_add") }}
              </button>
            </td>
            <td>
              <button class="x" :aria-label="t('account.wl_remove')" @click="removeOne(p)">✕</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- mobile cards -->
    <ul v-if="rows.length" class="cards">
      <li v-for="p in rows" :key="p.id" class="wcard">
        <RouterLink class="prod" :to="`/products/${p.slug}`">
          <span class="prod__img prod__img--lg">
            <img v-if="p.gallery[0]" :src="p.gallery[0].thumb_url" alt="" />
            <span v-else class="prod__ph" aria-hidden="true" />
          </span>
          <span class="wcard__meta">
            <b>{{ p.translation.name }}</b>
            <i class="tnum">{{ formatPrice(unitPrice(p)) }}</i>
            <span class="stock" :class="inStock(p) ? 'stock--in' : 'stock--out'">
              {{ inStock(p) ? t("account.wl_in_stock") : t("account.wl_out_stock") }}
            </span>
          </span>
        </RouterLink>
        <div class="wcard__actions">
          <button class="cta cta--sm" :disabled="!inStock(p) || busy === p.id" @click="addOne(p)">{{ t("account.wl_add") }}</button>
          <button class="x" :aria-label="t('account.wl_remove')" @click="removeOne(p)">✕</button>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: clamp(1rem, 3vw, 1.75rem); }
.head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 18px; }
.card__title { font-family: var(--font-display); font-size: 1.15rem; font-weight: 800; }
.head__actions { display: flex; gap: 8px; }
.muted { color: var(--text-subtle); }
.notice { background: var(--success-bg); color: var(--success-fg); border-radius: var(--radius-sm); padding: 9px 13px; font-size: 13px; margin-bottom: 14px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }

.cta { padding: 9px 16px; border: 0; border-radius: var(--radius-full); background: var(--accent); color: var(--on-accent); font-size: 12px; font-weight: 700; letter-spacing: .03em; text-transform: uppercase; cursor: pointer; white-space: nowrap; }
.cta:disabled { opacity: .5; cursor: default; }
.ghost { padding: 9px 16px; border: 1px solid var(--border-2); border-radius: var(--radius-full); background: none; color: var(--text-muted); font-size: 12px; font-weight: 700; cursor: pointer; }

.prod { display: flex; align-items: center; gap: 12px; text-decoration: none; color: var(--text); min-width: 0; }
.prod__img { width: 52px; height: 52px; border-radius: var(--radius-sm); overflow: hidden; background: var(--photo-well); border: 1px solid var(--border); flex-shrink: 0; display: grid; place-items: center; }
.prod__img--lg { width: 64px; height: 64px; }
.prod__img img { width: 100%; height: 100%; object-fit: cover; }
[data-theme="dark"] .prod__img img { filter: brightness(.88); }
.prod__ph { width: 100%; height: 100%; background: var(--surface-2); }
.prod b { font-size: 13.5px; font-weight: 600; }
.prod:hover b { color: var(--accent-text); }

.stock { font-size: 12px; font-weight: 700; }
.stock--in { color: var(--success-fg); }
.stock--out { color: var(--sale); }
.x { width: 30px; height: 30px; border-radius: 999px; border: 1px solid var(--border-2); background: none; color: var(--text-muted); font-size: 13px; cursor: pointer; }
.x:hover { border-color: var(--sale); color: var(--sale); }

/* mobile-first: cards visible, table hidden */
.tablewrap { display: none; }
.cards { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.wcard { border: 1px solid var(--border); border-radius: var(--radius-md); padding: 12px; display: flex; flex-direction: column; gap: 10px; }
.wcard__meta { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.wcard__meta i { font-style: normal; font-size: 13.5px; font-weight: 700; }
.wcard__actions { display: flex; align-items: center; justify-content: space-between; gap: 8px; }

@media (min-width: 768px) {
  .cards { display: none; }
  .tablewrap { display: block; overflow-x: auto; }
  .tbl { width: 100%; border-collapse: collapse; }
  .tbl th { text-align: start; font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--text-subtle); padding: 10px 12px; border-bottom: 1px solid var(--border); }
  .tbl td { padding: 12px; border-bottom: 1px solid var(--border); font-size: 13.5px; vertical-align: middle; }
  .tbl tr:last-child td { border-bottom: 0; }
}
</style>
