<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";

const route = useRoute();
const state = ref<"working" | "done" | "failed">("working");

onMounted(async () => {
  const token = String(route.query.token ?? "");
  if (!token) {
    state.value = "failed";
    return;
  }
  try {
    await api.verifyEmail(token);
    state.value = "done";
  } catch {
    state.value = "failed";
  }
});
</script>

<template>
  <main class="narrow">
    <div class="state" aria-live="polite">
      <template v-if="state === 'working'">
        <h1>Verifying…</h1>
        <p class="muted">One moment while we confirm your email.</p>
      </template>
      <template v-else-if="state === 'done'">
        <h1>✓ Email verified</h1>
        <p class="muted">You're all set — thanks for confirming.</p>
        <RouterLink class="btn btn--primary" to="/account">Go to your account</RouterLink>
      </template>
      <template v-else>
        <h1>This link didn't work</h1>
        <p class="muted">It may have expired. Sign in and request a fresh verification email.</p>
        <RouterLink class="btn btn--primary" to="/account">Go to your account</RouterLink>
      </template>
    </div>
  </main>
</template>

<style scoped>
.narrow { max-width: 420px; margin: 0 auto; padding: var(--space-16) var(--container-pad); }
h1 { font-size: var(--text-3xl); margin-bottom: var(--space-2); }
.muted { color: var(--color-text-muted); margin-bottom: var(--space-6); }
.state { text-align: center; padding: var(--space-8) 0; }
</style>
