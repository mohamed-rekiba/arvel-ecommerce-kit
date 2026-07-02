<script setup lang="ts">
import Button from "primevue/button";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError, type Product, type ReviewList, type Variant, api, formatPrice } from "../api";
import { useCart } from "../cart";
import { getCachedProduct } from "../product-cache";
import { type MessageKey, t } from "../locale";

const route = useRoute();
const router = useRouter();
const { add } = useCart();

// seed synchronously from the list cache so the image paints on the first frame — the View Transition
// needs the shared element present on the new page to morph into (else it degrades to a fade).
const cached = getCachedProduct(String(route.params.slug));
const product = ref<Product | null>(cached);
const status = ref<"loading" | "error" | "ready">(cached ? "ready" : "loading");
const selectedVariantId = ref<number | null>(
  cached?.variants?.find((v) => v.stock > 0)?.id ?? cached?.variants?.[0]?.id ?? null,
);
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

// --- reviews (S16) ---------------------------------------------------------------
const reviewData = ref<ReviewList | null>(null);
const reviewForm = reactive({ rating: 5, title: "", body: "" });
const reviewBusy = ref(false);
const reviewError = ref<string | null>(null);

async function loadReviews(slug: string) {
  try {
    reviewData.value = await api.reviews(slug);
  } catch {
    reviewData.value = null;
  }
}

async function submitReview() {
  if (!product.value) return;
  reviewBusy.value = true;
  reviewError.value = null;
  try {
    await api.submitReview(product.value.slug, {
      rating: reviewForm.rating,
      body: reviewForm.body,
      ...(reviewForm.title ? { title: reviewForm.title } : {}),
    });
    await loadReviews(product.value.slug);
  } catch (e) {
    reviewError.value =
      e instanceof ApiError && e.status === 403
        ? t("pdp.review_verified_only")
        : e instanceof ApiError
          ? Object.values(e.errors)[0]?.[0] ?? t("pdp.review_error")
          : t("pdp.review_error");
  } finally {
    reviewBusy.value = false;
  }
}

// back-in-stock (S17)
const alertState = ref<"idle" | "done" | "auth">("idle");

async function notifyMe() {
  if (!selectedVariant.value) return;
  try {
    await api.subscribeStockAlert(selectedVariant.value.id);
    alertState.value = "done";
  } catch (e) {
    alertState.value = e instanceof ApiError && e.status === 401 ? "auth" : "idle";
  }
}

function stars(avg: number): string {
  return "★".repeat(Math.round(avg)) + "☆".repeat(5 - Math.round(avg));
}
const selectedVariant = computed(() =>
  variants.value.find((v) => v.id === selectedVariantId.value) ?? null,
);
const canAdd = computed(() => selectedVariant.value != null && selectedVariant.value.stock > 0);

async function load() {
  if (!product.value) status.value = "loading"; // keep the cached image on screen while refreshing
  try {
    const p = await api.product(String(route.params.slug));
    product.value = p;
    void loadReviews(p.slug);
    selectedVariantId.value = p.variants?.find((v) => v.stock > 0)?.id ?? p.variants?.[0]?.id ?? null;
    status.value = "ready";
  } catch {
    if (!product.value) status.value = "error";
  }
}

// "Back to shop" should return to wherever the user actually came from (catalog with its filters, a
// search, home, …) — not always home. `history.state.back` is null only when there's no in-app entry
// to return to (a fresh load / direct link), so fall back to the catalog in that case.
function goBack() {
  if (window.history.state?.back) router.back();
  else router.push({ name: "catalog" });
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
      <p>{{ t("pdp.not_found") }}</p>
      <button class="btn" @click="goBack">{{ t("pdp.back") }}</button>
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
            :style="product ? { viewTransitionName: `product-${product.id}` } : {}"
          />
          <div v-else class="pdp__placeholder" aria-hidden="true" />
        </div>
        <div v-if="gallery.length > 1" class="pdp__thumbs">
          <button
            v-for="(img, i) in gallery"
            :key="img.id"
            class="pdp__thumb"
            :class="{ on: i === selected }"
            :aria-label="t('pdp.view_image', { n: i + 1 })"
            @click="selected = i"
          >
            <img :src="img.thumb_url" alt="" />
          </button>
        </div>
      </div>
      <div class="pdp__info">
        <button class="pdp__back" @click="goBack">{{ t("common.back") }} {{ t("pdp.back") }}</button>
        <p class="eyebrow" v-if="product.category">{{ product.category.translation.name }}</p>
        <h1>{{ product.translation.name }}</h1>
        <p class="pdp__price">{{ formatPrice(product.price_cents, product.currency) }}</p>
        <p v-if="product.translation.description" class="pdp__desc">
          {{ product.translation.description }}
        </p>

        <label v-if="variants.length" class="pdp__field">
          <span class="pdp__label">{{ t("pdp.variant") }}</span>
          <select v-model="selectedVariantId">
            <option v-for="v in variants" :key="v.id" :value="v.id" :disabled="v.stock <= 0">
              {{ v.name }} — {{ v.stock > 0 ? t("pdp.in_stock", { n: v.stock }) : t("pdp.sold_out") }}
            </option>
          </select>
        </label>

        <Button
          class="pdp__add"
          :label="added ? t('pdp.added') : adding ? t('card.adding') : canAdd ? t('pdp.add') : t('pdp.sold_out_label')"
          :disabled="!canAdd || adding"
          :loading="adding"
          @click="addToCart"
        />
        <div v-if="selectedVariant && selectedVariant.stock <= 0" class="pdp__alert" aria-live="polite">
          <p v-if="alertState === 'done'" class="pdp__alert-ok">✓ {{ t("pdp.alert_done") }}</p>
          <p v-else-if="alertState === 'auth'" class="pdp__alert-note">
            <RouterLink to="/account">{{ t("pdp.sign_in") }}</RouterLink> {{ t("pdp.alert_signin_tail") }}
          </p>
          <button v-else class="pdp__alert-btn" @click="notifyMe">{{ t("pdp.notify_me") }}</button>
        </div>
        <ul class="pdp__meta">
          <li>{{ t("pdp.free_returns") }}</li>
          <li>{{ t("pdp.ships") }}</li>
        </ul>
      </div>
    </div>

    <section v-if="product" class="reviews" :aria-label="t('pdp.reviews')">
      <h2>
        {{ t("pdp.reviews") }}
        <span v-if="reviewData && reviewData.rating_count > 0" class="reviews__avg">
          {{ stars(reviewData.rating_avg ?? 0) }} {{ reviewData.rating_avg }} · {{ reviewData.rating_count }}
        </span>
      </h2>

      <p v-if="!reviewData || reviewData.reviews.length === 0" class="reviews__empty">
        {{ t("pdp.no_reviews") }}
      </p>
      <ul v-else class="reviews__list">
        <li v-for="r in reviewData.reviews" :key="r.id" class="review">
          <div class="review__head">
            <span class="review__stars">{{ stars(r.rating) }}</span>
            <strong v-if="r.title">{{ r.title }}</strong>
            <span class="review__author">{{ r.author ?? t("pdp.verified_buyer") }}</span>
          </div>
          <p class="review__body">{{ r.body }}</p>
        </li>
      </ul>

      <div v-if="reviewData?.mine" class="reviews__mine">
        {{ t("pdp.your_review_is") }} <strong>{{ t(`review.${reviewData.mine.status}` as MessageKey) }}</strong
        ><span v-if="reviewData.mine.status === 'pending'"> — {{ t("pdp.pending_tail") }}</span>
      </div>
      <form v-else class="reviews__form" @submit.prevent="submitReview">
        <h3>{{ t("pdp.write_review") }}</h3>
        <label>
          <span>{{ t("pdp.rating") }}</span>
          <select v-model.number="reviewForm.rating">
            <option v-for="n in [5, 4, 3, 2, 1]" :key="n" :value="n">{{ stars(n) }}</option>
          </select>
        </label>
        <label><span>{{ t("pdp.title_optional") }}</span><input v-model.trim="reviewForm.title" type="text" /></label>
        <label><span>{{ t("pdp.your_review") }}</span><textarea v-model.trim="reviewForm.body" rows="3" required /></label>
        <p v-if="reviewError" class="reviews__error" role="alert">{{ reviewError }}</p>
        <Button type="submit" :label="reviewBusy ? t('pdp.sending') : t('pdp.submit_review')" :disabled="reviewBusy || !reviewForm.body" />
      </form>
    </section>
  </main>
</template>

<style scoped>
.pdp { max-width: var(--container-max); margin: 0 auto; padding: var(--space-12) var(--container-pad) 0; }
.pdp__grid, .pdp__skeleton { display: grid; grid-template-columns: 1fr; gap: var(--space-8); align-items: start; }
@media (min-width: 1024px) { .pdp__grid, .pdp__skeleton { grid-template-columns: 1fr 1fr; gap: var(--space-16); } }
.pdp__media { display: flex; flex-direction: column; gap: 12px; }
/* same 4:5 ratio as the card grid / hero (ProductCard.vue, HomeView.vue) — the View Transition morph
   animates the box between the old (card) and new (PDP) rects, and a mismatched aspect ratio makes the
   captured image visibly stretch/squish mid-animation. Matching ratios keeps the morph a clean scale. */
.pdp__main { aspect-ratio: 4 / 5; border-radius: var(--radius-lg); overflow: hidden; background: var(--surface-2); }
.pdp__main img { width: 100%; height: 100%; object-fit: cover; }
.pdp__placeholder { width: 100%; height: 100%; background: var(--surface-2); }
.pdp__thumbs { display: flex; gap: 10px; flex-wrap: wrap; }
.pdp__thumb { width: 64px; height: 80px; border-radius: var(--radius-md); overflow: hidden; border: 2px solid transparent; padding: 0; cursor: pointer; background: var(--surface-2); transition: border-color var(--motion-base); }
.pdp__thumb.on { border-color: var(--accent); }
.pdp__thumb img { width: 100%; height: 100%; object-fit: cover; }
.pdp__info { padding-top: var(--space-4); }
.pdp__back { display: inline-block; border: 0; background: none; padding: 0; cursor: pointer; font: inherit; color: var(--color-text-muted); text-decoration: none; font-size: var(--text-sm); margin-bottom: var(--space-8); transition: color var(--motion-base) var(--ease); }
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
.reviews { max-width: 720px; margin: var(--space-16) auto 0; padding: 0 var(--container-pad) var(--space-16); }
.reviews h2 { font-size: var(--text-2xl); display: flex; align-items: baseline; gap: var(--space-4); }
.reviews__avg { font-size: var(--text-sm); color: var(--color-text-muted); }
.reviews__empty { color: var(--color-text-muted); }
.reviews__list { list-style: none; margin: var(--space-4) 0; padding: 0; }
.review { padding: var(--space-4) 0; border-bottom: 1px solid var(--color-border); }
.review__head { display: flex; gap: var(--space-3); align-items: baseline; }
.review__stars { color: var(--color-warning, #b45309); letter-spacing: 2px; }
.review__author { font-size: var(--text-xs); color: var(--color-text-muted); margin-inline-start: auto; }
.review__body { margin: var(--space-2) 0 0; font-size: var(--text-sm); }
.reviews__mine { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-3) var(--space-4); font-size: var(--text-sm); margin-top: var(--space-4); }
.reviews__form { margin-top: var(--space-6); display: grid; gap: var(--space-3); max-width: 420px; }
.reviews__form h3 { margin: 0; font-size: var(--text-lg); }
.reviews__form label span { display: block; font-size: var(--text-sm); margin-bottom: var(--space-1); }
.reviews__form input, .reviews__form select, .reviews__form textarea { width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); color: var(--color-text); font: inherit; }
.reviews__error { color: var(--color-danger); font-size: var(--text-sm); margin: 0; }
.pdp__alert { margin-top: var(--space-3); }
.pdp__alert-btn { background: none; border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-2) var(--space-4); font: inherit; font-size: var(--text-sm); cursor: pointer; color: var(--color-text); }
.pdp__alert-ok { color: var(--color-success, #2e7d32); font-size: var(--text-sm); }
.pdp__alert-note { font-size: var(--text-sm); color: var(--color-text-muted); }
</style>
