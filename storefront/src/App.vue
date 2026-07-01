<script setup lang="ts">
import { onMounted } from "vue";
import { useCart } from "./cart";

const { count, refresh } = useCart();
onMounted(refresh);
</script>

<template>
  <header class="topbar">
    <RouterLink class="brand" to="/">arvel <span>shop</span></RouterLink>
    <nav aria-label="Primary">
      <RouterLink to="/cart">
        Cart<span v-if="count" class="badge" aria-label="items in cart">{{ count }}</span>
      </RouterLink>
      <RouterLink to="/account">Account</RouterLink>
    </nav>
  </header>
  <RouterView />
  <footer class="foot">Arvel Shop — a reference storefront on the arvel framework.</footer>
</template>

<style scoped>
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-4) var(--container-pad); border-bottom: 1px solid var(--color-border);
  max-width: var(--container-max); margin: 0 auto;
}
.brand { font-weight: var(--weight-semibold); font-size: var(--text-lg); text-decoration: none; color: var(--color-text); }
.brand span { color: var(--color-accent); }
nav a { margin-left: var(--space-4); text-decoration: none; color: var(--color-text-muted); }
nav a:hover { color: var(--color-text); }
nav a.router-link-active { color: var(--color-text); }
.badge {
  display: inline-block; min-width: 1.25rem; margin-left: 4px; padding: 0 6px;
  background: var(--color-accent); color: var(--color-text-inverse);
  border-radius: var(--radius-full); font-size: var(--text-xs); text-align: center; line-height: 1.25rem;
}
.foot { max-width: var(--container-max); margin: var(--space-16) auto 0; padding: var(--space-8) var(--container-pad); border-top: 1px solid var(--color-border); color: var(--color-text-muted); font-size: var(--text-sm); }
</style>
