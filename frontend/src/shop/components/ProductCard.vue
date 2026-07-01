<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { type Product, formatPrice } from "../api";
import { useCart } from "../cart";

const props = defineProps<{ product: Product }>();
const router = useRouter();
const { add } = useCart();
const busy = ref(false);

const variants = computed(() => props.product.variants ?? []);
const soldOut = computed(() => variants.value.length > 0 && variants.value.every((v) => v.stock <= 0));
// cards are large — use the 600×750 `preview` conversion, not the 256×320 thumb (which upscales/softens)
const image = computed(() => props.product.gallery[0]?.preview_url ?? props.product.gallery[0]?.url ?? null);
const name = computed(() => props.product.translation.name);

async function addToBag() {
  const inStock = variants.value.filter((v) => v.stock > 0);
  if (inStock.length === 1) {
    busy.value = true;
    try { await add(inStock[0].id, 1); } finally { busy.value = false; }
  } else {
    router.push(`/products/${props.product.slug}`);
  }
}
</script>

<template>
  <article class="card" :class="{ 'card--out': soldOut }">
    <RouterLink class="media" :to="`/products/${product.slug}`" :aria-label="name">
      <img v-if="image" :src="image" :alt="name" loading="lazy" />
      <div v-else class="media__ph" aria-hidden="true" />
      <span v-if="soldOut" class="media__out">Sold out</span>
      <button v-else class="add" :disabled="busy" @click.prevent.stop="addToBag">
        {{ busy ? "Adding…" : "Add to bag" }}
      </button>
    </RouterLink>
    <div class="info">
      <RouterLink class="name" :to="`/products/${product.slug}`">{{ name }}</RouterLink>
      <span class="price tnum">{{ formatPrice(product.price_cents, product.currency) }}</span>
    </div>
  </article>
</template>

<style scoped>
.card { display: flex; flex-direction: column; }
.card--out { opacity: .7; }
.media { position: relative; display: block; aspect-ratio: 4 / 5; border-radius: var(--radius-lg); overflow: hidden; background: var(--surface-2); }
.media img { width: 100%; height: 100%; object-fit: cover; transition: transform 1s var(--ease-out); }
.card:hover .media img { transform: scale(1.045); }
.media__ph { width: 100%; height: 100%; background: linear-gradient(150deg, var(--surface-2), color-mix(in srgb, var(--accent) 8%, var(--surface-2))); }
.media__out { position: absolute; top: 14px; left: 14px; background: color-mix(in srgb, var(--bg) 85%, transparent); color: var(--text-muted); font-size: 11px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; padding: 5px 11px; border-radius: var(--radius-full); backdrop-filter: blur(6px); }
.add { position: absolute; left: 14px; right: 14px; bottom: 14px; height: 44px; border: 0; border-radius: var(--radius-md); background: color-mix(in srgb, var(--bg) 88%, transparent); backdrop-filter: blur(8px); color: var(--text); font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; opacity: 0; transform: translateY(8px); transition: opacity var(--motion-base) var(--ease), transform var(--motion-base) var(--ease), background var(--motion-base); }
.card:hover .add, .add:focus-visible { opacity: 1; transform: translateY(0); }
.add:hover { background: var(--accent); color: var(--on-accent); }
.add:disabled { opacity: .6; cursor: default; }
.info { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; padding: 16px 2px 0; }
.name { font-size: 15px; font-weight: 500; color: var(--text); text-decoration: none; line-height: 1.4; }
.name:hover { color: var(--accent); }
.price { font-family: var(--font-display); font-size: 15px; font-weight: 600; color: var(--text-muted); white-space: nowrap; }
@media (hover: none) { .add { opacity: 1; transform: none; background: var(--surface); border: 1px solid var(--border); } }
</style>
