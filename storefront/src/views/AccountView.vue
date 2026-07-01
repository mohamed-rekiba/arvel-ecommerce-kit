<script setup lang="ts">
// Placeholder account view — the storefront checkout is guest-first (cart by X-Cart-Token). Full
// customer auth (register/login via the bearer-token API) is a follow-up; this documents the entry point.
</script>

<template>
  <main class="account">
    <h1>Account</h1>
    <p class="account__note">
      You're shopping as a guest — your cart travels with you via a secure token. Sign-in and order
      history are available through the API (register / login) and land here next.
    </p>
    <RouterLink class="btn" to="/">Back to shop</RouterLink>
  </main>
</template>

<style scoped>
.account { max-width: 560px; margin: 0 auto; padding: var(--space-8) var(--container-pad); }
.account h1 { font-size: var(--text-2xl); margin-bottom: var(--space-4); }
.account__note { color: var(--color-text-muted); line-height: 1.6; margin-bottom: var(--space-6); }
.btn { display: inline-block; padding: var(--space-3) var(--space-5); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); text-decoration: none; color: var(--color-text); }
</style>
