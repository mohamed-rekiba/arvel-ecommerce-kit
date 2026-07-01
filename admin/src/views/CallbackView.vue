<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuth } from "../auth";
import { completeKeycloakLogin } from "../oidc";

const router = useRouter();
const { restore } = useAuth();
const error = ref<string | null>(null);

onMounted(async () => {
  const params = new URLSearchParams(location.search);
  const code = params.get("code");
  if (params.get("error") || !code) {
    error.value = params.get("error_description") || "Sign-in was cancelled.";
    return;
  }
  try {
    await completeKeycloakLogin(code);
    await restore(); // populate the signed-in user for the shell (App mounted before the token existed)
    router.replace("/dashboard");
  } catch {
    error.value = "Keycloak sign-in failed. Please try again.";
  }
});
</script>

<template>
  <div class="callback">
    <div v-if="error" class="callback__box">
      <p class="callback__error">{{ error }}</p>
      <RouterLink class="btn" to="/login">Back to sign in</RouterLink>
    </div>
    <div v-else class="callback__box">
      <span class="spinner" aria-hidden="true" />
      <p>Signing you in with Keycloak…</p>
    </div>
  </div>
</template>

<style scoped>
.callback { display: grid; place-items: center; min-height: 100vh; }
.callback__box { display: flex; flex-direction: column; align-items: center; gap: var(--space-4); color: var(--color-text-muted); }
.callback__error { color: var(--color-danger); }
.spinner { width: 28px; height: 28px; border: 3px solid var(--color-border); border-top-color: var(--color-accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
