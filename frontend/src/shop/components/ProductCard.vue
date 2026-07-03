<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { type Product, authToken, formatPrice } from "../api";
import { useCart } from "../cart";
import { t } from "../locale";
import { useWishlist } from "../wishlist";

const props = defineProps<{ product: Product }>();
const router = useRouter();
const { add } = useCart();
const { has, toggle } = useWishlist();
const busy = ref(false);
const added = ref(false);

const saved = computed(() => has(props.product.id));
async function toggleSave() {
  if (!authToken.get()) return router.push("/account");
  await toggle(props.product.id);
}

const variants = computed(() => props.product.variants ?? []);
const soldOut = computed(() => variants.value.length > 0 && variants.value.every((v) => v.stock <= 0));
const starRow = computed(() => {
  const full = Math.round(props.product.rating_avg ?? 0);
  return "★".repeat(full) + "☆".repeat(5 - full);
});

// badges: a live deal shows −N%; a recent product shows NEW (14-day window)
const deal = computed(() => props.product.deal ?? null);
const isNew = computed(() => {
  if (!props.product.created_at) return false;
  const created = new Date(props.product.created_at).getTime();
  return Date.now() - created < 14 * 24 * 3600 * 1000;
});

// serve all three conversions via srcset so the browser picks the suitable one per viewport/DPR:
// thumb 256w (small/2-up on phones), preview 600w (cards), original 900w (retina). `src` = preview fallback.
const g = computed(() => props.product.gallery[0] ?? null);
const image = computed(() => g.value?.preview_url ?? g.value?.url ?? null);
const srcset = computed(() =>
  g.value ? `${g.value.thumb_url} 256w, ${g.value.preview_url} 600w, ${g.value.url} 900w` : undefined,
);
const name = computed(() => props.product.translation.name);

async function addToBag() {
  const inStock = variants.value.filter((v) => v.stock > 0);
  if (inStock.length === 1) {
    busy.value = true;
    try {
      await add(inStock[0].id, 1);
      added.value = true;
      setTimeout(() => (added.value = false), 1400);
    } finally {
      busy.value = false;
    }
  } else {
    router.push(`/products/${props.product.slug}`);
  }
}
</script>

<template>
  <article class="card" :class="{ 'card--out': soldOut }">
    <RouterLink class="media" :to="`/products/${product.slug}`" :aria-label="name">
      <img
        v-if="image"
        :src="image"
        :srcset="srcset"
        sizes="(max-width: 560px) 100vw, (max-width: 1024px) 50vw, 25vw"
        :alt="name"
        loading="lazy"
        :style="{ viewTransitionName: `product-${product.id}` }"
      />
      <div v-else class="media__ph" aria-hidden="true" />
      <div class="badges">
        <span v-if="deal" class="badge badge--deal">−{{ deal.percent_off }}%</span>
        <span v-else-if="isNew" class="badge badge--new">{{ t("card.new") }}</span>
      </div>
      <button
        class="heart"
        :class="{ on: saved }"
        :aria-label="saved ? t('card.unsave') : t('card.save')"
        @click.prevent.stop="toggleSave"
      >
        {{ saved ? "♥" : "♡" }}
      </button>
      <span v-if="soldOut" class="media__out">{{ t("card.soldout") }}</span>
    </RouterLink>
    <div class="info">
      <RouterLink class="name" :to="`/products/${product.slug}`">{{ name }}</RouterLink>
      <div v-if="product.rating_count > 0" class="stars" :aria-label="`${(product.rating_avg ?? 0).toFixed(1)} / 5`">
        <span class="stars__row" aria-hidden="true">{{ starRow }}</span>
        <span class="stars__n">({{ product.rating_count }})</span>
      </div>
      <div class="prices">
        <template v-if="deal">
          <s class="prices__old tnum">{{ formatPrice(product.price_cents, product.currency) }}</s>
          <span class="prices__now prices__now--sale tnum">{{ formatPrice(deal.deal_price_cents, product.currency) }}</span>
        </template>
        <span v-else class="prices__now tnum">{{ formatPrice(product.price_cents, product.currency) }}</span>
      </div>
      <button class="add" :disabled="busy || soldOut" @click.prevent.stop="addToBag">
        {{ added ? t("pdp.added") : busy ? t("card.adding") : soldOut ? t("card.soldout") : t("card.add") }}
      </button>
    </div>
  </article>
</template>

<style scoped>
.card { display: flex; flex-direction: column; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; transition: box-shadow var(--motion-base), transform var(--motion-base); }
.card:hover { box-shadow: var(--shadow-2); }
.card--out { opacity: .75; }
.media { position: relative; display: block; aspect-ratio: 1 / 1; overflow: hidden; background: var(--photo-well); }
/* dark: the well becomes an inset "framed tile" — card surface visible around it — and a cool
   veil pulls warm photo whites toward the neutral register */
[data-theme="dark"] .media { margin: 8px 8px 0; aspect-ratio: auto; height: 0; padding-bottom: calc(100% - 16px); border-radius: var(--radius-md); }
[data-theme="dark"] .media::after { content: ""; position: absolute; inset: 0; background: rgb(19 20 23 / .05); pointer-events: none; }
[data-theme="dark"] .media img { position: absolute; inset: 0; }
.media img { width: 100%; height: 100%; object-fit: cover; transition: transform .8s var(--ease-out); }
/* dark: dim imagery ~12% (thumbnail-dimming pattern) so white-background shots don't glare */
[data-theme="dark"] .media img { filter: brightness(.88); }
.card:hover .media img { transform: scale(1.04); }
.media__ph { width: 100%; height: 100%; background: var(--surface-2); }
.badges { position: absolute; top: 10px; inset-inline-start: 10px; display: flex; flex-direction: column; gap: 6px; }
.badge { font-size: 11px; font-weight: 800; letter-spacing: .04em; padding: 4px 9px; border-radius: var(--radius-sm); }
.badge--deal { background: var(--accent-bright); color: var(--on-accent-bright); }
.badge--new { background: var(--text); color: var(--bg); }
.media__out { position: absolute; bottom: 10px; inset-inline-start: 10px; background: color-mix(in srgb, var(--surface) 88%, transparent); color: var(--text-muted); font-size: 11px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; padding: 4px 10px; border-radius: var(--radius-full); backdrop-filter: blur(6px); }
/* 44px touch target per DESIGN.md */
.heart { position: absolute; top: 8px; inset-inline-end: 8px; width: 44px; height: 44px; border-radius: 999px; border: 0; background: color-mix(in srgb, var(--surface) 82%, transparent); backdrop-filter: blur(6px); color: var(--text-muted); font-size: 15px; line-height: 1; cursor: pointer; display: grid; place-items: center; box-shadow: var(--shadow-1); transition: color var(--motion-base), transform var(--motion-base); }
.heart:hover { transform: scale(1.08); color: var(--accent-text); }
.heart.on { color: var(--accent-text); }
.info { display: flex; flex-direction: column; gap: 6px; padding: 12px 14px 14px; border-top: 1px solid var(--border); }
.name { font-size: 13.5px; font-weight: 500; color: var(--text); text-decoration: none; line-height: 1.4; min-height: 2.6em; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.name:hover { color: var(--accent-text); }
.stars { display: flex; align-items: center; gap: 6px; }
.stars__row { color: var(--star); font-size: 12px; letter-spacing: .06em; }
.stars__n { color: var(--text-subtle); font-size: 11.5px; }
.prices { display: flex; align-items: baseline; gap: 8px; }
.prices__old { color: var(--text-subtle); font-size: 12.5px; }
.prices__now { font-family: var(--font-display); font-size: 16px; font-weight: 700; color: var(--text); }
.prices__now--sale { color: var(--sale); }
.add { margin-top: 4px; height: 38px; border: 1px solid var(--accent); border-radius: var(--radius-full); background: transparent; color: var(--accent-text); font: inherit; font-size: 12.5px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; cursor: pointer; transition: background var(--motion-base), color var(--motion-base); }
.add:hover:not(:disabled) { background: var(--accent); color: var(--on-accent); }
.add:disabled { opacity: .55; cursor: default; }
</style>
