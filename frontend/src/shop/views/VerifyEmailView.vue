<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { t } from '../locale'

const route = useRoute()
const state = ref<'working' | 'done' | 'failed'>('working')

onMounted(async () => {
  const token = String(route.query.token ?? '')
  const id = Number(route.query.id ?? 0)
  if (!token || !id) {
    state.value = 'failed'
    return
  }
  try {
    await api.verifyEmail(id, token)
    state.value = 'done'
  } catch {
    state.value = 'failed'
  }
})
</script>

<template>
  <main class="narrow">
    <div class="state" aria-live="polite">
      <template v-if="state === 'working'">
        <h1>{{ t('auth.verifying') }}</h1>
        <p class="muted">{{ t('auth.verifying_sub') }}</p>
      </template>
      <template v-else-if="state === 'done'">
        <h1>✓ {{ t('auth.verified') }}</h1>
        <p class="muted">{{ t('auth.verified_sub') }}</p>
        <RouterLink class="btn btn--primary" to="/account">{{ t('auth.go_account') }}</RouterLink>
      </template>
      <template v-else>
        <h1>{{ t('auth.verify_failed') }}</h1>
        <p class="muted">{{ t('auth.verify_failed_sub') }}</p>
        <RouterLink class="btn btn--primary" to="/account">{{ t('auth.go_account') }}</RouterLink>
      </template>
    </div>
  </main>
</template>

<style scoped>
.narrow {
  max-width: 420px;
  margin: 0 auto;
  padding: var(--space-16) var(--container-pad);
}
h1 {
  font-size: var(--text-3xl);
  margin-bottom: var(--space-2);
}
.muted {
  color: var(--color-text-muted);
  margin-bottom: var(--space-6);
}
.state {
  text-align: center;
  padding: var(--space-8) 0;
}
</style>
