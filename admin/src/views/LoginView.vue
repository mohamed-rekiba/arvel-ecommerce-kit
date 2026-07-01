<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError } from "../api";
import { useAuth } from "../auth";

const router = useRouter();
const { login } = useAuth();

const email = ref("catalog@example.com");
const password = ref("secret-admin");
const error = ref<string | null>(null);
const busy = ref(false);

async function submit() {
  busy.value = true;
  error.value = null;
  try {
    await login(email.value, password.value);
    router.push("/dashboard");
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 401 ? "Invalid credentials." : "Sign-in failed.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="login">
    <div class="login__card">
      <div class="brand">
        <span class="brand__mark" aria-hidden="true" />
        <span class="brand__name">Arvel <span>Console</span></span>
      </div>
      <h1 class="login__title">Sign in</h1>
      <p class="login__sub">Back-office access for the Arvel store.</p>

      <form class="form" @submit.prevent="submit">
        <label class="field">
          <span class="field__label">Email</span>
          <input v-model="email" class="input" type="email" autocomplete="username" required />
        </label>
        <label class="field">
          <span class="field__label">Password</span>
          <input v-model="password" class="input" type="password" autocomplete="current-password" required />
        </label>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="btn btn--primary submit" :disabled="busy" type="submit">
          {{ busy ? "Signing in…" : "Sign in" }}
        </button>
      </form>

      <div class="hint">
        <p class="hint__title">Seeded roles · password <code>secret-admin</code></p>
        <ul>
          <li><code>super-admin@example.com</code> — everything</li>
          <li><code>catalog@example.com</code> — catalog</li>
          <li><code>orders@example.com</code> — orders</li>
          <li><code>support@example.com</code> — read-only + audit</li>
        </ul>
      </div>
      <p class="oidc">Production sign-in uses Keycloak (OIDC); the same roles map through.</p>
    </div>
  </div>
</template>

<style scoped>
.login { display: grid; place-items: center; min-height: 100vh; padding: var(--space-6); }
.login__card { width: 100%; max-width: 400px; background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-lg); box-shadow: var(--shadow-2); padding: var(--space-8); }
.brand { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-6); }
.brand__mark { width: 24px; height: 24px; border-radius: 6px; background: var(--color-accent); position: relative; }
.brand__mark::after { content: ""; position: absolute; inset: 7px; border: 2px solid var(--color-text-inverse); border-radius: 2px; }
.brand__name { font-weight: var(--weight-semibold); font-size: var(--text-lg); }
.brand__name span { color: var(--color-text-muted); font-weight: var(--weight-regular); }
.login__title { font-size: var(--text-2xl); }
.login__sub { color: var(--color-text-muted); margin: var(--space-1) 0 var(--space-6); }
.form { display: flex; flex-direction: column; gap: var(--space-4); }
.field { display: flex; flex-direction: column; gap: var(--space-2); }
.field__label { font-size: var(--text-sm); font-weight: var(--weight-medium); }
.error { color: var(--color-danger); font-size: var(--text-sm); margin: 0; }
.submit { width: 100%; padding: var(--space-3); }
.hint { margin-top: var(--space-6); padding: var(--space-4); background: var(--color-surface); border-radius: var(--radius-md); }
.hint__title { font-size: var(--text-xs); color: var(--color-text-muted); margin: 0 0 var(--space-2); }
.hint ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-1); }
.hint li { font-size: var(--text-xs); color: var(--color-text-muted); }
code { font-family: ui-monospace, monospace; font-size: 0.95em; color: var(--color-text); }
.oidc { font-size: var(--text-xs); color: var(--color-text-faint); text-align: center; margin: var(--space-4) 0 0; }
</style>
