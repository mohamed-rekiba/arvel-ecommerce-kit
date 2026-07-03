<script setup lang="ts">
// A "Deals of the Day" card per the reference: image, −N% badge, name, stars, struck + sale
// price, the available/sold sell-through bar, and a live countdown.
import { computed } from "vue";
import { type Deal, formatPrice } from "../api";
import { t } from "../locale";
import CountdownTimer from "./CountdownTimer.vue";

const props = defineProps<{ deal: Deal }>();

const product = computed(() => props.deal.product);
const image = computed(
  () => product.value.gallery[0]?.preview_url ?? product.value.gallery[0]?.url ?? null,
);
const starRow = computed(() => {
  const full = Math.round(product.value.rating_avg ?? 0);
  return "★".repeat(full) + "☆".repeat(5 - full);
});
const soldPct = computed(() => {
  const total = props.deal.available + props.deal.sold;
  return total === 0 ? 0 : Math.round((props.deal.sold / total) * 100);
});
</script>

<template>
  <article class="deal">
    <RouterLink class="deal__media" :to="`/products/${product.slug}`" :aria-label="product.translation.name">
      <img v-if="image" :src="image" :alt="product.translation.name" loading="lazy" />
      <div v-else class="deal__ph" aria-hidden="true" />
      <span class="deal__badge">−{{ deal.percent_off }}%</span>
    </RouterLink>
    <div class="deal__info">
      <RouterLink class="deal__name" :to="`/products/${product.slug}`">
        {{ product.translation.name }}
      </RouterLink>
      <div v-if="product.rating_count > 0" class="deal__stars" :aria-label="`${(product.rating_avg ?? 0).toFixed(1)} / 5`">
        <span aria-hidden="true" class="deal__starrow">{{ starRow }}</span>
        <span class="deal__starn">({{ product.rating_count }})</span>
      </div>
      <p class="deal__prices">
        <s class="tnum">{{ formatPrice(product.price_cents, product.currency) }}</s>
        <b class="tnum">{{ formatPrice(deal.deal_price_cents, product.currency) }}</b>
      </p>
      <div class="deal__stock">
        <div class="deal__stockrow">
          <span>{{ t("deal.available") }}: <b>{{ deal.available }}</b></span>
          <span>{{ t("deal.sold") }}: <b>{{ deal.sold }}</b></span>
        </div>
        <div class="deal__bar" role="progressbar" :aria-valuenow="soldPct" aria-valuemin="0" aria-valuemax="100" :aria-label="t('deal.sold')">
          <div class="deal__fill" :style="{ width: `${soldPct}%` }" />
        </div>
      </div>
      <CountdownTimer :ends-at="deal.ends_at" />
    </div>
  </article>
</template>

<style scoped>
.deal { display: grid; grid-template-columns: 1fr; gap: 16px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 18px; }
.deal__media { position: relative; display: block; aspect-ratio: 1 / 1; border-radius: var(--radius-md); overflow: hidden; background: var(--photo-well); }
.deal__media img { width: 100%; height: 100%; object-fit: cover; }
[data-theme="dark"] .deal__media img { filter: brightness(.88); }
.deal__ph { width: 100%; height: 100%; background: var(--surface-2); }
.deal__badge { position: absolute; top: 10px; inset-inline-start: 10px; background: var(--accent-bright); color: var(--on-accent-bright); font-size: 12px; font-weight: 800; padding: 4px 10px; border-radius: var(--radius-sm); }
.deal__info { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.deal__name { font-size: 15px; font-weight: 600; color: var(--text); text-decoration: none; line-height: 1.35; }
.deal__name:hover { color: var(--accent-text); }
.deal__stars { display: flex; align-items: center; gap: 6px; }
.deal__starrow { color: var(--star); font-size: 12.5px; letter-spacing: .06em; }
.deal__starn { color: var(--text-subtle); font-size: 11.5px; }
.deal__prices { display: flex; align-items: baseline; gap: 10px; margin: 0; }
.deal__prices s { color: var(--text-subtle); font-size: 13.5px; }
.deal__prices b { font-family: var(--font-display); font-size: 20px; font-weight: 800; color: var(--sale); }
.deal__stock { display: flex; flex-direction: column; gap: 5px; }
.deal__stockrow { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted); }
.deal__bar { height: 6px; border-radius: var(--radius-full); background: var(--surface-2); border: 1px solid var(--border); overflow: hidden; }
.deal__fill { height: 100%; background: var(--accent-bright); border-radius: inherit; transition: width var(--motion-slow) var(--ease); }
@media (min-width: 640px) {
  .deal { grid-template-columns: minmax(0, .9fr) 1.1fr; align-items: center; }
}
</style>
