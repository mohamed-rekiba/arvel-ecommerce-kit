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
    router.push("/products");
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 401 ? "Invalid credentials." : "Sign-in failed.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="login">
    <form class="login__card" @submit.prevent="submit">
      <div class="login__brand">arvel <span>admin</span></div>
      <p class="login__hint">Back-office sign-in. Seeded roles: super-admin@, catalog@, orders@, support@ (password <code>secret-admin</code>).</p>

      <label>
        <span>Email</span>
        <input v-model="email" type="email" autocomplete="username" required />
      </label>
      <label>
        <span>Password</span>
        <input v-model="password" type="password" autocomplete="current-password" required />
      </label>

      <p v-if="error" class="login__error" role="alert">{{ error }}</p>
      <button class="btn btn--primary" :disabled="busy" type="submit">
        {{ busy ? "Signing in…" : "Sign in" }}
      </button>
      <p class="login__oidc">Production login uses Keycloak (OIDC) — the same roles map through.</p>
    </form>
  </div>
</template>

<style scoped>
.login { display: grid; place-items: center; min-height: 100vh; padding: var(--space-4); }
.login__card { width: 100%; max-width: 380px; display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-8); border: 1px solid var(--color-border); border-radius: var(--radius-lg); }
.login__brand { font-weight: var(--weight-semibold); font-size: var(--text-xl); }
.login__brand span { color: var(--color-accent); }
.login__hint { font-size: var(--text-sm); color: var(--color-text-muted); }
.login__card label { display: flex; flex-direction: column; gap: var(--space-1); font-size: var(--text-sm); }
.login__card input { padding: var(--space-2) var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); font: inherit; }
.login__error { color: var(--color-danger, #b00020); font-size: var(--text-sm); margin: 0; }
.btn--primary { padding: var(--space-3); border: none; border-radius: var(--radius-md); background: var(--color-accent); color: var(--color-text-inverse); cursor: pointer; font: inherit; }
.btn--primary:disabled { opacity: 0.5; }
.login__oidc { font-size: var(--text-xs); color: var(--color-text-muted); text-align: center; margin: 0; }
</style>
