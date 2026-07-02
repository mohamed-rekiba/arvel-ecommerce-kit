<script setup lang="ts">
import { ref } from "vue";
import { useRoute } from "vue-router";
import { ApiError, api } from "../api";

const route = useRoute();
const token = String(route.query.token ?? "");
const password = ref("");
const done = ref(false);
const busy = ref(false);
const error = ref<string | null>(null);

async function submit() {
  busy.value = true;
  error.value = null;
  try {
    await api.resetPassword(token, password.value);
    done.value = true;
  } catch (e) {
    error.value =
      e instanceof ApiError && e.status === 422
        ? Object.values(e.errors)[0]?.[0] ?? "This reset link is invalid or has expired."
        : "Something went wrong. Please try again.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="narrow">
    <div v-if="done" class="state">
      <h1>Password updated</h1>
      <p class="muted">You can sign in with your new password now.</p>
      <RouterLink class="btn btn--primary" to="/account">Sign in</RouterLink>
    </div>
    <div v-else-if="!token" class="state">
      <h1>Invalid link</h1>
      <p class="muted">This reset link is missing its token — request a new one.</p>
      <RouterLink class="btn btn--primary" to="/forgot-password">Request a new link</RouterLink>
    </div>
    <template v-else>
      <h1>Choose a new password</h1>
      <form class="form" @submit.prevent="submit">
        <label class="field">
          <span>New password</span>
          <input
            v-model="password"
            type="password"
            autocomplete="new-password"
            minlength="8"
            required
          />
        </label>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="btn btn--primary" type="submit" :disabled="busy">
          {{ busy ? "Saving…" : "Set new password" }}
        </button>
        <p class="muted"><RouterLink to="/forgot-password">Link expired? Request a new one.</RouterLink></p>
      </form>
    </template>
  </main>
</template>

<style scoped>
.narrow { max-width: 420px; margin: 0 auto; padding: var(--space-16) var(--container-pad); }
h1 { font-size: var(--text-3xl); margin-bottom: var(--space-4); }
.muted { color: var(--color-text-muted); margin: var(--space-4) 0; }
.form .field { display: block; margin-bottom: var(--space-4); }
.field span { display: block; font-size: var(--text-sm); margin-bottom: var(--space-1); }
.field input { width: 100%; padding: var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); color: var(--color-text); font: inherit; }
.error { color: var(--color-danger); font-size: var(--text-sm); margin-bottom: var(--space-3); }
.state { text-align: center; padding: var(--space-8) 0; }
</style>
