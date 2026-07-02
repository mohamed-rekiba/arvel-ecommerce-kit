<script setup lang="ts">
// Ticks client-side toward an ISO deadline (the deal's ends_at). Emits nothing; parents that
// need expiry behavior watch the deal list itself (the server is the authority on live deals).
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { t } from "../locale";

const props = defineProps<{ endsAt: string; compact?: boolean }>();

const now = ref(Date.now());
let timer: ReturnType<typeof setInterval> | null = null;
onMounted(() => {
  timer = setInterval(() => (now.value = Date.now()), 1000);
});
onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});

const parts = computed(() => {
  const remaining = Math.max(0, new Date(props.endsAt).getTime() - now.value);
  const s = Math.floor(remaining / 1000);
  return [
    { v: Math.floor(s / 86400), label: t("deal.days") },
    { v: Math.floor((s % 86400) / 3600), label: t("deal.hrs") },
    { v: Math.floor((s % 3600) / 60), label: t("deal.mins") },
    { v: s % 60, label: t("deal.secs") },
  ];
});
</script>

<template>
  <div class="cd" :class="{ 'cd--compact': compact }" role="timer" :aria-label="t('deal.ends_in')">
    <div v-for="(p, i) in parts" :key="i" class="cd__cell">
      <b class="tnum">{{ String(p.v).padStart(2, "0") }}</b>
      <i>{{ p.label }}</i>
    </div>
  </div>
</template>

<style scoped>
.cd { display: flex; gap: 8px; }
.cd__cell { display: flex; flex-direction: column; align-items: center; min-width: 46px; padding: 6px 4px; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius-sm); }
.cd__cell b { font-family: var(--font-display); font-size: 16px; font-weight: 800; line-height: 1.1; color: var(--text); }
.cd__cell i { font-style: normal; font-size: 9.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--text-subtle); }
.cd--compact .cd__cell { min-width: 38px; padding: 4px 2px; }
.cd--compact .cd__cell b { font-size: 13px; }
</style>
