<script setup lang="ts">
// A 503 from any API call (arvel down) swaps in the maintenance screen until a retry succeeds.
import { onMounted, ref } from 'vue'

import { makeT } from './lib/i18n'

// App.vue is the shared root (shop and admin each own their message chunks), so the maintenance
// strings live in a tiny colocated map rather than dragging either section's map in here.
const t = makeT({
  en: {
    'maintenance.title': 'Back in a moment',
    'maintenance.body': "We're doing a little maintenance. Your cart is safe — try again shortly.",
    'maintenance.retry': 'Try again'
  },
  fr: {
    'maintenance.title': 'De retour dans un instant',
    'maintenance.body':
      'Nous effectuons une petite maintenance. Votre panier est en sécurité — réessayez sous peu.',
    'maintenance.retry': 'Réessayer'
  },
  ar: {
    'maintenance.title': 'سنعود بعد لحظات',
    'maintenance.body':
      'نقوم بأعمال صيانة بسيطة. سلة التسوق الخاصة بك بأمان — حاول مجددًا بعد قليل.',
    'maintenance.retry': 'حاول مرة أخرى'
  }
})

const down = ref(false)

async function retry() {
  try {
    const res = await fetch('/api/health')
    if (res.ok) {
      down.value = false
      window.location.reload()
    }
  } catch {
    /* still down */
  }
}

onMounted(() => {
  window.addEventListener('arvel:maintenance', () => {
    down.value = true
  })
})
</script>

<template>
  <div v-if="down" class="maintenance" role="alert">
    <div class="maintenance__card">
      <p class="maintenance__mark">⏸</p>
      <h1>{{ t('maintenance.title') }}</h1>
      <p>{{ t('maintenance.body') }}</p>
      <button class="maintenance__retry" @click="retry">{{ t('maintenance.retry') }}</button>
    </div>
  </div>
  <RouterView v-else />
</template>

<style scoped>
.maintenance {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: var(--color-bg);
  color: var(--color-text);
  padding: var(--space-8);
}
.maintenance__card {
  text-align: center;
  max-width: 380px;
}
.maintenance__mark {
  font-size: 40px;
  margin: 0 0 var(--space-3);
}
.maintenance__card h1 {
  font-size: var(--text-2xl);
  margin: 0 0 var(--space-2);
}
.maintenance__card p {
  color: var(--color-text-muted);
}
.maintenance__retry {
  margin-top: var(--space-5);
  padding: var(--space-3) var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit;
  cursor: pointer;
}
</style>
