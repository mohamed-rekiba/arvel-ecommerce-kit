<script setup lang="ts">
import Button from "primevue/button";
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

// gallery with a selected image (lead with the sharp `original` 900×1125, preview as the 1x fallback)
const selected = ref(0);
const gallery = computed(() => product.value?.gallery ?? []);
const g = computed(() => gallery.value[selected.value] ?? null);
const image = computed(() => g.value?.url ?? g.value?.preview_url ?? null);
const srcset = computed(() => (g.value ? `${g.value.preview_url} 600w, ${g.value.url} 900w` : undefined));
watch(product, () => (selected.value = 0));
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
        <div class="pdp__main">
          <img
            v-if="image"
            :src="image"
            :srcset="srcset"
            sizes="(max-width: 900px) 100vw, 44vw"
            :alt="product.translation.name"
          />
          <div v-else class="pdp__placeholder" aria-hidden="true" />
        </div>
        <div v-if="gallery.length > 1" class="pdp__thumbs">
          <button
            v-for="(img, i) in gallery"
            :key="img.id"
            class="pdp__thumb"
            :class="{ on: i === selected }"
            :aria-label="`View image ${i + 1}`"
            @click="selected = i"
          >
            <img :src="img.thumb_url" alt="" />
          </button>
        </div>
      </div>
      <div class="pdp__info">
        <RouterLink class="pdp__back" to="/">← Back to shop</RouterLink>
        <p class="eyebrow" v-if="product.category">{{ product.category.translation.name }}</p>
        <h1>{{ product.translation.name }}</h1>
        <p class="pdp__price">{{ formatPrice(product.price_cents, product.currency) }}</p>
        <p v-if="product.translation.description" class="pdp__desc">
          {{ product.translation.description }}
        </p>

        <label v-if="variants.length" class="pdp__field">
          <span class="pdp__label">Variant</span>
          <select v-model="selectedVariantId">
            <option v-for="v in variants" :key="v.id" :value="v.id" :disabled="v.stock <= 0">
              {{ v.name }} — {{ v.stock > 0 ? `${v.stock} in stock` : "sold out" }}
            </option>
          </select>
        </label>

        <Button
          class="pdp__add"
          :label="added ? 'Added to cart ✓' : adding ? 'Adding…' : canAdd ? 'Add to cart' : 'Sold out'"
          :disabled="!canAdd || adding"
          :loading="adding"
          @click="addToCart"
        />
        <ul class="pdp__meta">
          <li>Free returns within 30 days</li>
          <li>Ships in 2–4 business days</li>
        </ul>
      </div>
    </div>
  </main>
</template>

<style scoped>
.pdp { max-width: var(--container-max); margin: 0 auto; padding: var(--space-12) var(--container-pad) 0; }
.pdp__grid, .pdp__skeleton { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-16); align-items: start; }
@media (max-width: 820px) { .pdp__grid, .pdp__skeleton { grid-template-columns: 1fr; gap: var(--space-8); } }
.pdp__media { display: flex; flex-direction: column; gap: 12px; }
.pdp__main { aspect-ratio: 3 / 4; border-radius: var(--radius-lg); overflow: hidden; background: var(--surface-2); }
.pdp__main img { width: 100%; height: 100%; object-fit: cover; }
.pdp__placeholder { width: 100%; height: 100%; background: var(--surface-2); }
.pdp__thumbs { display: flex; gap: 10px; flex-wrap: wrap; }
.pdp__thumb { width: 64px; height: 80px; border-radius: var(--radius-md); overflow: hidden; border: 2px solid transparent; padding: 0; cursor: pointer; background: var(--surface-2); transition: border-color var(--motion-base); }
.pdp__thumb.on { border-color: var(--accent); }
.pdp__thumb img { width: 100%; height: 100%; object-fit: cover; }
.pdp__info { padding-top: var(--space-4); }
.pdp__back { display: inline-block; color: var(--color-text-muted); text-decoration: none; font-size: var(--text-sm); margin-bottom: var(--space-8); transition: color var(--motion-base) var(--ease); }
.pdp__back:hover { color: var(--color-text); }
.pdp__info h1 { font-size: var(--text-3xl); margin: var(--space-2) 0 var(--space-4); }
.pdp__price { font-size: var(--text-xl); color: var(--color-text); margin: 0 0 var(--space-6); }
.pdp__desc { color: var(--color-text-muted); line-height: var(--leading-normal); max-width: 48ch; }
.pdp__field { display: block; margin: var(--space-8) 0 var(--space-6); max-width: 22rem; }
.pdp__label { display: block; font-size: var(--text-sm); font-weight: var(--weight-medium); margin-bottom: var(--space-2); }
.pdp__field select { width: 100%; padding: var(--space-3) var(--space-4); border: 1px solid var(--color-border-strong); border-radius: var(--radius-md); background: var(--color-bg); font: inherit; }
.pdp__add { width: 100%; max-width: 22rem; padding: var(--space-4); }
.pdp__meta { list-style: none; margin: var(--space-6) 0 0; padding: var(--space-6) 0 0; border-top: 1px solid var(--color-border); display: flex; flex-direction: column; gap: var(--space-2); color: var(--color-text-muted); font-size: var(--text-sm); }
.skeleton { background: var(--color-surface); border-radius: var(--radius-md); animation: pulse 1.4s var(--ease) infinite; }
.skeleton--media { aspect-ratio: 3 / 4; border-radius: var(--radius-lg); }
.skeleton--text { height: 2.5rem; margin-top: var(--space-8); }
@keyframes pulse { 50% { opacity: 0.55; } }
</style>
