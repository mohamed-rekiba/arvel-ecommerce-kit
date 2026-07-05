<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../auth'
import { completeKeycloakLogin } from '../oidc'
import { t } from '../locale'

const router = useRouter()
const { restore } = useAuth()
const error = ref<string | null>(null)

onMounted(async () => {
  const params = new URLSearchParams(location.search)
  const code = params.get('code')
  if (params.get('error') || !code) {
    error.value = params.get('error_description') || t('login.cancelled')
    return
  }
  try {
    await completeKeycloakLogin(code)
    await restore() // populate the signed-in user for the shell (App mounted before the token existed)
    router.replace('/admin/dashboard')
  } catch {
    error.value = t('login.keycloak_failed')
  }
})
</script>

<template>
  <div class="callback">
    <div v-if="error" class="callback__box">
      <p class="callback__error">{{ error }}</p>
      <RouterLink class="btn" to="/admin/login">{{ t('login.back') }}</RouterLink>
    </div>
    <div v-else class="callback__box">
      <span class="spinner" aria-hidden="true" />
      <p>{{ t('login.with_keycloak') }}</p>
    </div>
  </div>
</template>

<style scoped>
.callback {
  display: grid;
  place-items: center;
  min-height: 100vh;
}
.callback__box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  color: var(--color-text-muted);
}
.callback__error {
  color: var(--color-danger);
}
.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
