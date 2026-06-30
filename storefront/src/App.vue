<script setup lang="ts">
import CatalogView from "./views/CatalogView.vue";
</script>

<template>
  <header class="topbar">
    <a class="brand" href="/">arvel <span>shop</span></a>
    <nav aria-label="Primary">
      <a href="/cart">Cart</a>
      <a href="/account">Account</a>
    </nav>
  </header>
  <CatalogView />
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
.foot { max-width: var(--container-max); margin: var(--space-16) auto 0; padding: var(--space-8) var(--container-pad); border-top: 1px solid var(--color-border); color: var(--color-text-muted); font-size: var(--text-sm); }
</style>
