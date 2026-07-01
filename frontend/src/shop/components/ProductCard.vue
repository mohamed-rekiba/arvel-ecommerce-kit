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
const image = computed(() => props.product.gallery[0]?.thumb_url ?? null);
const name = computed(() => props.product.translation.name);
const kicker = computed(() => props.product.category?.translation.name ?? "Shop");

async function addToCart() {
  const inStock = variants.value.filter((v) => v.stock > 0);
  // one obvious variant → add it here; otherwise let the customer choose on the product page
  if (inStock.length === 1) {
    busy.value = true;
    try { await add(inStock[0].id, 1); } finally { busy.value = false; }
  } else {
    router.push(`/products/${props.product.slug}`);
  }
}
</script>

<template>
  <div class="card" :class="{ 'card--soldout': soldOut }">
    <RouterLink class="card__media" :to="`/products/${product.slug}`" :aria-label="name">
      <img v-if="image" :src="image" :alt="name" loading="lazy" />
      <div v-else class="card__obj" aria-hidden="true" />
      <span v-if="soldOut" class="card__badge">Sold out</span>
      <span class="card__heart" aria-hidden="true">♡</span>
    </RouterLink>
    <div class="card__body">
      <span class="card__kicker">{{ kicker }}</span>
      <RouterLink class="card__name" :to="`/products/${product.slug}`">{{ name }}</RouterLink>
      <p class="card__price tnum">{{ formatPrice(product.price_cents, product.currency) }}</p>
      <button class="card__add" :disabled="soldOut || busy" @click="addToCart">
        {{ soldOut ? "Sold out" : busy ? "Adding…" : "Add to cart" }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-1); display: flex; flex-direction: column; transition: box-shadow var(--motion-base) var(--ease); }
.card:hover { box-shadow: var(--shadow-2); }
.card--soldout { opacity: .72; }
.card__media { position: relative; aspect-ratio: 1; background: var(--surface-2); display: grid; place-items: center; overflow: hidden; }
.card__media img { width: 100%; height: 100%; object-fit: cover; transition: transform var(--motion-slow) var(--ease); }
.card:hover .card__media img { transform: scale(1.05); }
.card__obj { width: 66%; height: 66%; border-radius: 12px; background: linear-gradient(150deg, color-mix(in srgb, var(--text-subtle) 35%, transparent), color-mix(in srgb, var(--text-subtle) 15%, transparent)); }
.card__badge { position: absolute; top: 10px; left: 10px; background: var(--sale); color: #fff; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: var(--radius-full); }
.card__heart { position: absolute; top: 10px; right: 10px; width: 30px; height: 30px; border-radius: 999px; background: var(--surface); display: grid; place-items: center; box-shadow: var(--shadow-1); color: var(--text-muted); }
.card__body { padding: 14px; display: flex; flex-direction: column; gap: 5px; }
.card__kicker { font-size: 11px; color: var(--text-subtle); font-weight: 600; }
.card__name { font-size: 13.5px; font-weight: 600; color: var(--text); text-decoration: none; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 38px; }
.card__name:hover { color: var(--amber-600); }
.card__price { font-family: var(--font-display); font-weight: 800; font-size: 17px; margin: 2px 0 0; }
.card__add { margin-top: 8px; height: 38px; border-radius: var(--radius-full); border: 1px solid var(--amber-500); background: transparent; color: var(--amber-600); font-weight: 700; font-size: 13px; cursor: pointer; transition: background var(--motion-base) var(--ease), color var(--motion-base) var(--ease); }
.card__add:hover:not(:disabled) { background: var(--amber-500); color: var(--on-accent); }
.card__add:disabled { opacity: .5; cursor: not-allowed; }
</style>
