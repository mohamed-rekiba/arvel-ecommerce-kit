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
  <a
    class="card"
    :class="{ 'card--soldout': soldOut }"
    :href="soldOut ? undefined : `/products/${product.slug}`"
    :aria-disabled="soldOut"
  >
    <div class="card__media">
      <img v-if="image" :src="image" :alt="name" loading="lazy" />
      <div v-else class="card__placeholder" aria-hidden="true" />
      <span v-if="soldOut" class="card__chip">Sold out</span>
    </div>
    <h3 class="card__name">{{ name }}</h3>
    <p class="card__price">{{ formatPrice(product.price_cents, product.currency) }}</p>
  </a>
</template>

<style scoped>
.card {
  display: block;
  text-decoration: none;
  color: var(--color-text);
  border-radius: var(--radius-md);
  transition: box-shadow var(--motion-base) var(--ease), transform var(--motion-base) var(--ease);
}
.card:hover:not(.card--soldout) {
  box-shadow: var(--shadow-2);
  transform: translateY(-2px);
}
.card--soldout { cursor: not-allowed; opacity: 0.55; }
.card__media {
  position: relative;
  aspect-ratio: 4 / 5;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.card__media img { width: 100%; height: 100%; object-fit: cover; }
.card__placeholder { width: 100%; height: 100%; background: var(--color-surface); }
.card__chip {
  position: absolute; top: var(--space-2); left: var(--space-2);
  background: var(--color-text); color: var(--color-text-inverse);
  font-size: var(--text-xs); padding: 2px var(--space-2); border-radius: var(--radius-full);
}
.card__name { margin: var(--space-3) 0 var(--space-1); font-size: var(--text-base); font-weight: var(--weight-medium); }
.card__price { margin: 0; font-size: var(--text-sm); color: var(--color-text-muted); }
</style>
