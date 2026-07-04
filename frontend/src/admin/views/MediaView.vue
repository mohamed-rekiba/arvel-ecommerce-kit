<script setup lang="ts">
// Read-only: deletion lives with the owning resource (product editor / banners / avatar replace).
import { computed, onMounted, ref } from "vue";
import { type MediaItem, ApiError, api } from "../api";
import { type MessageKey, t } from "../locale";

const items = ref<MediaItem[]>([]);
const loading = ref(true);
const notice = ref<string | null>(null);
const filter = ref<string>("");

const TYPES = ["product", "banner", "user"] as const;
const shown = computed(() =>
  filter.value ? items.value.filter((m) => m.owner_type === filter.value) : items.value,
);

function ownerRoute(m: MediaItem): string | null {
  if (m.owner_type === "product") return `/admin/products/${m.owner_id}`;
  if (m.owner_type === "banner") return "/admin/banners";
  if (m.owner_type === "user") return `/admin/users`;
  return null;
}

function fmtSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${bytes} B`;
}

async function load() {
  loading.value = true;
  notice.value = null;
  try {
    items.value = await api.adminMedia();
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t("common.no_catalog") : t("common.load_error");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="page">
    <header class="head">
      <p class="eyebrow">{{ t("media.eyebrow") }}</p>
      <h1>{{ t("nav.media") }}</h1>
      <p class="sub">{{ t("media.sub") }}</p>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="chips" role="group" :aria-label="t('media.owner')">
      <button class="chip" :class="{ on: filter === '' }" @click="filter = ''">{{ t("orders.all") }}</button>
      <button
        v-for="ty in TYPES"
        :key="ty"
        class="chip"
        :class="{ on: filter === ty }"
        @click="filter = ty"
      >{{ t(`media.type_${ty}` as MessageKey) }}</button>
    </div>

    <p v-if="loading" class="muted">{{ t("common.loading") }}</p>
    <p v-else-if="!shown.length" class="muted">{{ t("media.none") }}</p>

    <div v-else class="grid">
      <article v-for="m in shown" :key="m.id" class="card">
        <a class="card__img" :href="m.url" target="_blank" rel="noopener">
          <img :src="m.thumb_url ?? m.url" :alt="m.file_name" loading="lazy" />
        </a>
        <div class="card__meta">
          <RouterLink v-if="ownerRoute(m)" class="card__owner" :to="ownerRoute(m)!">
            {{ m.owner_label }}
          </RouterLink>
          <span v-else class="card__owner">{{ m.owner_label }}</span>
          <span class="card__facts">
            <i class="tag">{{ t(`media.type_${m.owner_type}` as MessageKey) }}</i>
            <i>{{ m.collection }}</i>
          </span>
          <span class="card__file" :title="m.file_name">{{ m.file_name }}</span>
          <span class="card__size">{{ fmtSize(m.size) }} · {{ m.mime_type }}</span>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: .16em; color: var(--accent); font-weight: 600; }
.head { margin-bottom: 20px; }
.head h1 { font-family: var(--font-display); font-size: 26px; font-weight: 700; letter-spacing: -.02em; margin: 6px 0 2px; }
.sub { color: var(--text-muted); font-size: 13px; margin: 0; }
.notice { background: var(--danger-bg); color: var(--danger-fg); padding: 10px 14px; border-radius: var(--radius-md); font-size: 13px; margin-bottom: 16px; }
.muted { color: var(--text-subtle); }

.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
.chip { padding: 7px 14px; border-radius: 999px; border: 1px solid var(--border); background: var(--surface); color: var(--text-muted); font-size: 12.5px; font-weight: 600; cursor: pointer; text-transform: capitalize; }
.chip.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-1); }
.card__img { display: block; aspect-ratio: 4 / 3; background: var(--photo-well); }
.card__img img { width: 100%; height: 100%; object-fit: cover; }
.card__meta { padding: 10px 12px; display: flex; flex-direction: column; gap: 3px; }
.card__owner { font-size: 13px; font-weight: 600; color: var(--text); text-decoration: none; }
a.card__owner:hover { color: var(--accent); }
.card__facts { display: flex; gap: 6px; }
.card__facts i { font-style: normal; font-size: 10.5px; color: var(--text-subtle); text-transform: capitalize; }
.card__facts .tag { background: var(--surface-2); border-radius: 999px; padding: 1px 8px; }
.card__file { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card__size { font-size: 11px; color: var(--text-subtle); }
</style>
