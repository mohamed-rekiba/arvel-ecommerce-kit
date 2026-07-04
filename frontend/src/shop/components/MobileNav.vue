<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import type { Category } from "../api";
import { t } from "../locale";

const props = defineProps<{ open: boolean; categories?: Category[] }>();
const emit = defineEmits<{ close: [] }>();

// A template ref on <RouterLink> yields the component instance, not the DOM node — reach the element via `$el`.
const firstLink = ref<{ $el: HTMLAnchorElement } | null>(null);
const showCats = ref(false);

// Not a full focus trap; returning focus to the trigger button on close is the parent's job (it owns that ref).
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) void nextTick(() => firstLink.value?.$el?.focus());
  },
);
</script>

<template>
  <Transition name="mnav">
    <div v-if="open" class="mnav">
      <div class="mnav__backdrop" @click="emit('close')" />
      <nav
        id="mobile-nav-panel"
        class="mnav__panel"
        role="dialog"
        aria-modal="true"
        :aria-label="t('a11y.primary')"
        @keydown.escape="emit('close')"
      >
        <RouterLink ref="firstLink" to="/" class="mnav__link" @click="emit('close')">{{ t("nav.home") }}</RouterLink>
        <RouterLink :to="{ name: 'catalog' }" class="mnav__link" @click="emit('close')">{{ t("nav.shop") }}</RouterLink>
        <button class="mnav__link mnav__acc" :aria-expanded="showCats" @click="showCats = !showCats">
          {{ t("nav.collections") }} <span aria-hidden="true">{{ showCats ? "▴" : "▾" }}</span>
        </button>
        <div v-if="showCats" class="mnav__cats">
          <RouterLink
            v-for="c in categories ?? []"
            :key="c.id"
            class="mnav__cat"
            :to="{ name: 'catalog', query: { category: c.slug } }"
            @click="emit('close')"
          >
            {{ c.translation.name }}
          </RouterLink>
        </div>
        <RouterLink to="/deals" class="mnav__link mnav__link--deal" @click="emit('close')">{{ t("nav.deals") }}</RouterLink>
        <RouterLink to="/" class="mnav__link" @click="emit('close')">{{ t("nav.about") }}</RouterLink>
      </nav>
    </div>
  </Transition>
</template>

<style scoped>
.mnav__backdrop {
  position: fixed; inset: 0; z-index: var(--z-overlay);
  background: color-mix(in srgb, var(--ink-950) 45%, transparent);
}
.mnav__panel {
  position: fixed; top: 0; inset-inline-start: 0; bottom: 0; z-index: var(--z-modal);
  width: min(78vw, 320px);
  display: flex; flex-direction: column; gap: 4px;
  padding: calc(var(--space-8) + env(safe-area-inset-top, 0px)) var(--space-6) var(--space-8);
  background: var(--surface); border-inline-end: 1px solid var(--border);
  box-shadow: var(--shadow-3);
  overflow-y: auto;
}
.mnav__link {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-3) 0; font-size: 15px; font-weight: 600;
  letter-spacing: .02em; color: var(--text); text-decoration: none;
  border: 0; background: none; font-family: inherit; cursor: pointer; text-align: start;
  transition: color var(--motion-base);
}
.mnav__link:hover, .mnav__link:focus-visible { color: var(--accent-text); }
.mnav__link--deal { color: var(--accent-text); }
.mnav__cats { display: flex; flex-direction: column; padding-inline-start: var(--space-4); }
.mnav__cat { padding: var(--space-2) 0; font-size: 14px; color: var(--text-muted); text-decoration: none; }
.mnav__cat:hover { color: var(--accent-text); }

.mnav-enter-active, .mnav-leave-active { transition: opacity var(--motion-base) var(--ease); }
.mnav-enter-active .mnav__panel, .mnav-leave-active .mnav__panel { transition: transform var(--motion-slow) var(--ease-out); }
.mnav-enter-from, .mnav-leave-to { opacity: 0; }
.mnav-enter-from .mnav__panel, .mnav-leave-to .mnav__panel { transform: translateX(-100%); }
[dir="rtl"] .mnav-enter-from .mnav__panel, [dir="rtl"] .mnav-leave-to .mnav__panel { transform: translateX(100%); }
</style>
