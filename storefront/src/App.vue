<script setup lang="ts">
import { onMounted } from "vue";
import { useCart } from "./cart";

const { count, refresh } = useCart();
onMounted(refresh);
</script>

<template>
  <header class="topbar">
    <div class="topbar__inner">
      <RouterLink class="brand" to="/" aria-label="Arvel Shop home">
        <span class="brand__mark" aria-hidden="true" />
        <span class="brand__word">Arvel</span>
      </RouterLink>
      <nav class="nav" aria-label="Primary">
        <RouterLink to="/">Shop</RouterLink>
        <RouterLink to="/account">Account</RouterLink>
        <RouterLink class="nav__cart" to="/cart">
          Cart
          <span v-if="count" class="badge" aria-label="items in cart">{{ count }}</span>
        </RouterLink>
      </nav>
    </div>
  </header>

  <RouterView />

  <footer class="foot">
    <div class="foot__inner">
      <div class="foot__brand">
        <span class="brand__mark" aria-hidden="true" />
        <span>Arvel Shop</span>
      </div>
      <p>A reference storefront on the arvel framework — editorial commerce, done calmly.</p>
    </div>
  </footer>
</template>

<style scoped>
.topbar {
  position: sticky; top: 0; z-index: 20;
  background: color-mix(in srgb, var(--color-bg) 82%, transparent);
  backdrop-filter: saturate(140%) blur(12px);
  border-bottom: 1px solid var(--color-border);
}
.topbar__inner {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-4) var(--container-pad); max-width: var(--container-max); margin: 0 auto;
}
.brand { display: inline-flex; align-items: center; gap: var(--space-2); text-decoration: none; }
.brand__word { font-family: var(--font-display); font-size: var(--text-xl); letter-spacing: var(--tracking-tight); color: var(--color-text); }
.brand__mark {
  width: 18px; height: 18px; border-radius: 5px;
  border: 2.5px solid var(--color-accent); position: relative;
}
.brand__mark::after { content: ""; position: absolute; inset: 3px; border-radius: 1px; background: var(--color-accent); opacity: 0.18; }
.nav { display: flex; align-items: center; gap: var(--space-6); }
.nav a { text-decoration: none; color: var(--color-text-muted); font-size: var(--text-sm); font-weight: var(--weight-medium); transition: color var(--motion-base) var(--ease); }
.nav a:hover, .nav a.router-link-active { color: var(--color-text); }
.nav__cart { display: inline-flex; align-items: center; gap: var(--space-2); }
.badge {
  display: inline-flex; align-items: center; justify-content: center; min-width: 1.25rem; height: 1.25rem; padding: 0 5px;
  background: var(--color-accent); color: var(--color-text-inverse);
  border-radius: var(--radius-full); font-size: var(--text-xs); font-weight: var(--weight-semibold);
}
.foot { margin-top: var(--space-24); border-top: 1px solid var(--color-border); background: var(--color-surface); }
.foot__inner { max-width: var(--container-max); margin: 0 auto; padding: var(--space-12) var(--container-pad); }
.foot__brand { display: inline-flex; align-items: center; gap: var(--space-2); font-family: var(--font-display); font-size: var(--text-lg); }
.foot p { color: var(--color-text-muted); font-size: var(--text-sm); margin: var(--space-3) 0 0; max-width: 42ch; }
</style>
