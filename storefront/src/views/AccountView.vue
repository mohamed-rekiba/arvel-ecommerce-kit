<script setup lang="ts">
// Placeholder account view — the storefront checkout is guest-first (cart by X-Cart-Token). Full
// customer auth (register/login via the bearer-token API) is a follow-up; this documents the entry point.
</script>

<template>
  <main class="account">
    <p class="eyebrow">Your account</p>
    <h1>Guest checkout</h1>
    <p class="account__note">
      You're shopping as a guest — your cart travels with you via a secure token, so nothing is lost
      between visits. Sign-in and order history are served by the API (register / login) and arrive here next.
    </p>
    <RouterLink class="btn btn--primary" to="/">Back to the collection</RouterLink>
  </main>
</template>

<style scoped>
.account { max-width: 560px; margin: 0 auto; padding: var(--space-20) var(--container-pad) 0; }
.account h1 { font-size: var(--text-3xl); margin: var(--space-2) 0 var(--space-5); }
.account__note { color: var(--color-text-muted); line-height: var(--leading-normal); margin-bottom: var(--space-8); max-width: 52ch; }
</style>
