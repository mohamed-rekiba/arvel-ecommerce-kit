<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { type Product, type Variant, api, formatPrice } from "../api";
import { useCart } from "../cart";

const route = useRoute();
const router = useRouter();
const { add } = useCart();

const product = ref<Product | null>(null);
const status = ref<"loading" | "error" | "ready">("loading");
const selectedVariantId = ref<number | null>(null);
const adding = ref(false);
const added = ref(false);

const image = computed(() => product.value?.gallery[0]?.preview_url ?? null);
const variants = computed<Variant[]>(() => product.value?.variants ?? []);
const selectedVariant = computed(() =>
  variants.value.find((v) => v.id === selectedVariantId.value) ?? null,
);
const canAdd = computed(() => selectedVariant.value != null && selectedVariant.value.stock > 0);

async function load() {
  status.value = "loading";
  try {
    const p = await api.product(String(route.params.slug));
    product.value = p;
    selectedVariantId.value = p.variants?.find((v) => v.stock > 0)?.id ?? p.variants?.[0]?.id ?? null;
    status.value = "ready";
  } catch {
    status.value = "error";
  }
}

async function addToCart() {
  if (selectedVariantId.value == null) return;
  adding.value = true;
  try {
    await add(selectedVariantId.value, 1);
    added.value = true;
    setTimeout(() => (added.value = false), 1500);
  } finally {
    adding.value = false;
  }
}

onMounted(load);
watch(() => route.params.slug, load);
</script>

<template>
  <main class="pdp">
    <div v-if="status === 'loading'" class="pdp__skeleton" aria-busy="true">
      <div class="skeleton skeleton--media" />
      <div class="skeleton skeleton--text" />
    </div>

    <div v-else-if="status === 'error'" class="state" role="alert">
      <p>This product could not be found.</p>
      <button class="btn" @click="router.push('/')">Back to shop</button>
    </div>

    <div v-else-if="product" class="pdp__grid">
      <div class="pdp__media">
        <img v-if="image" :src="image" :alt="product.translation.name" />
        <div v-else class="pdp__placeholder" aria-hidden="true" />
      </div>
      <div class="pdp__info">
        <RouterLink class="pdp__back" to="/">← Shop</RouterLink>
        <h1>{{ product.translation.name }}</h1>
        <p class="pdp__price">{{ formatPrice(product.price_cents, product.currency) }}</p>
        <p v-if="product.translation.description" class="pdp__desc">
          {{ product.translation.description }}
        </p>

        <label v-if="variants.length" class="pdp__field">
          <span>Variant</span>
          <select v-model="selectedVariantId">
            <option v-for="v in variants" :key="v.id" :value="v.id" :disabled="v.stock <= 0">
              {{ v.name }} — {{ v.stock > 0 ? `${v.stock} in stock` : "sold out" }}
            </option>
          </select>
        </label>

        <button class="btn btn--primary" :disabled="!canAdd || adding" @click="addToCart">
          {{ added ? "Added ✓" : adding ? "Adding…" : canAdd ? "Add to cart" : "Sold out" }}
        </button>
      </div>
    </div>
  </main>
</template>

<style scoped>
.pdp { max-width: var(--container-max); margin: 0 auto; padding: var(--space-8) var(--container-pad); }
.pdp__grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-8); }
@media (max-width: 720px) { .pdp__grid { grid-template-columns: 1fr; } }
.pdp__media { aspect-ratio: 4 / 5; border: 1px solid var(--color-border); border-radius: var(--radius-md); overflow: hidden; background: var(--color-surface); }
.pdp__media img { width: 100%; height: 100%; object-fit: cover; }
.pdp__placeholder { width: 100%; height: 100%; background: var(--color-surface); }
.pdp__back { color: var(--color-text-muted); text-decoration: none; font-size: var(--text-sm); }
.pdp__info h1 { margin: var(--space-2) 0; font-size: var(--text-2xl); }
.pdp__price { font-size: var(--text-xl); color: var(--color-text); margin: 0 0 var(--space-4); }
.pdp__desc { color: var(--color-text-muted); line-height: 1.6; }
.pdp__field { display: block; margin: var(--space-4) 0; }
.pdp__field span { display: block; font-size: var(--text-sm); color: var(--color-text-muted); margin-bottom: var(--space-1); }
.pdp__field select { width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); }
.btn { padding: var(--space-3) var(--space-5); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); cursor: pointer; font: inherit; }
.btn--primary { background: var(--color-accent); color: var(--color-text-inverse); border-color: var(--color-accent); }
.btn--primary:disabled { opacity: 0.5; cursor: not-allowed; }
.skeleton { background: var(--color-surface); border-radius: var(--radius-md); animation: pulse 1.2s ease-in-out infinite; }
.skeleton--media { aspect-ratio: 4 / 5; }
.skeleton--text { height: 2rem; margin-top: var(--space-4); }
.pdp__skeleton { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-8); }
@keyframes pulse { 50% { opacity: 0.5; } }
</style>
