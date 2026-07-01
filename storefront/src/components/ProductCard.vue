<script setup lang="ts">
import { computed } from "vue";
import { type Product, formatPrice } from "../api";

const props = defineProps<{ product: Product }>();

const soldOut = computed(
  () => (props.product.variants ?? []).every((v) => v.stock <= 0) &&
    (props.product.variants ?? []).length > 0,
);
const image = computed(() => props.product.gallery[0]?.thumb_url ?? null);
const name = computed(() => props.product.translation.name);
</script>

<template>
  <RouterLink
    class="card"
    :class="{ 'card--soldout': soldOut }"
    :to="`/products/${product.slug}`"
    :aria-disabled="soldOut"
  >
    <div class="card__media">
      <img v-if="image" :src="image" :alt="name" loading="lazy" />
      <div v-else class="card__placeholder" aria-hidden="true" />
      <span v-if="soldOut" class="card__chip">Sold out</span>
      <span class="card__cta">View</span>
    </div>
    <div class="card__body">
      <h3 class="card__name">{{ name }}</h3>
      <p class="card__price">{{ formatPrice(product.price_cents, product.currency) }}</p>
    </div>
  </RouterLink>
</template>

<style scoped>
.card {
  display: block; text-decoration: none; color: var(--color-text);
}
.card--soldout { opacity: 0.6; }
.card__media {
  position: relative; aspect-ratio: 3 / 4; overflow: hidden;
  background: var(--color-surface); border-radius: var(--radius-md);
}
.card__media img {
  width: 100%; height: 100%; object-fit: cover;
  transition: transform var(--motion-slow) var(--ease);
}
.card:hover:not(.card--soldout) .card__media img { transform: scale(1.04); }
.card__placeholder { width: 100%; height: 100%; background: var(--color-surface-2); }
.card__chip {
  position: absolute; top: var(--space-3); left: var(--space-3);
  background: var(--color-bg); color: var(--color-text);
  font-size: var(--text-xs); font-weight: var(--weight-medium);
  padding: 3px var(--space-3); border-radius: var(--radius-full); box-shadow: var(--shadow-1);
}
.card__cta {
  position: absolute; bottom: var(--space-3); left: 50%; transform: translate(-50%, 8px);
  background: var(--color-bg); color: var(--color-text); font-size: var(--text-sm); font-weight: var(--weight-medium);
  padding: var(--space-2) var(--space-5); border-radius: var(--radius-full); box-shadow: var(--shadow-2);
  opacity: 0; transition: opacity var(--motion-base) var(--ease), transform var(--motion-base) var(--ease);
}
.card:hover:not(.card--soldout) .card__cta { opacity: 1; transform: translate(-50%, 0); }
.card--soldout .card__cta { display: none; }
.card__body { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-3); margin-top: var(--space-4); }
.card__name { font-family: var(--font-display); font-size: var(--text-lg); font-weight: var(--weight-regular); }
.card__price { margin: 0; font-size: var(--text-sm); color: var(--color-text-muted); white-space: nowrap; }
</style>
