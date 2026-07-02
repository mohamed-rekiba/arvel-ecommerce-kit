<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: [] }>();

// a template ref on <RouterLink> yields the component instance, not the DOM node — its root element
// is reachable via `$el` (a Vue-exposed property on every component instance).
const firstLink = ref<{ $el: HTMLAnchorElement } | null>(null);

// move focus into the drawer on open — a lightweight a11y baseline (not a full focus trap; returning
// focus to the trigger button on close is the parent's job, since it owns that button's ref).
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
        aria-label="Primary"
        @keydown.escape="emit('close')"
      >
        <RouterLink ref="firstLink" :to="{ name: 'catalog' }" class="mnav__link" @click="emit('close')">Shop</RouterLink>
        <RouterLink to="/" class="mnav__link" @click="emit('close')">Collections</RouterLink>
        <RouterLink to="/" class="mnav__link" @click="emit('close')">About</RouterLink>
      </nav>
    </div>
  </Transition>
</template>

<style scoped>
.mnav__backdrop {
  position: fixed; inset: 0; z-index: var(--z-overlay);
  background: color-mix(in srgb, var(--ink-900) 45%, transparent);
}
.mnav__panel {
  position: fixed; top: 0; left: 0; bottom: 0; z-index: var(--z-modal);
  width: min(78vw, 320px);
  display: flex; flex-direction: column; gap: 4px;
  padding: calc(var(--space-8) + env(safe-area-inset-top, 0px)) var(--space-6) var(--space-8);
  background: var(--bg); border-right: 1px solid var(--border);
  box-shadow: var(--shadow-3);
}
.mnav__link {
  padding: var(--space-3) 0; font-size: 15px; font-weight: 500;
  letter-spacing: .02em; color: var(--text-muted); text-decoration: none;
  transition: color var(--motion-base);
}
.mnav__link:hover, .mnav__link:focus-visible { color: var(--text); }

/* plain CSS transition, not the View Transitions API — this is an in-page toggle, not a navigation,
   and reusing the router-driven VT here would risk colliding with the ::view-transition-group(*) morph
   if a drawer-close and a route-change VT ever fire in the same tick (e.g. tapping a nav link). This
   inherits the existing prefers-reduced-motion block in base.css for free (it's a plain transition,
   not a view-transition-* pseudo-element). */
.mnav-enter-active .mnav__panel, .mnav-leave-active .mnav__panel { transition: transform var(--motion-slow) var(--ease-out); }
.mnav-enter-active .mnav__backdrop, .mnav-leave-active .mnav__backdrop { transition: opacity var(--motion-base) var(--ease-out); }
.mnav-enter-from .mnav__panel, .mnav-leave-to .mnav__panel { transform: translateX(-100%); }
.mnav-enter-from .mnav__backdrop, .mnav-leave-to .mnav__backdrop { opacity: 0; }

@media (min-width: 640px) { .mnav { display: none; } }
</style>

