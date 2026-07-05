<script setup lang="ts">
// Server-authoritative: only deals inside their window arrive here; countdowns just tick client-side.
import { onMounted, ref } from 'vue'
import { type Deal, api } from '../api'
import DealCard from '../components/DealCard.vue'
import { t } from '../locale'

const deals = ref<Deal[]>([])
const status = ref<'loading' | 'error' | 'ready'>('loading')

async function load() {
  status.value = 'loading'
  try {
    deals.value = await api.deals()
    status.value = 'ready'
  } catch {
    status.value = 'error'
  }
}
onMounted(load)
</script>

<template>
  <main class="dealspage">
    <header class="head">
      <p class="eyebrow">{{ t('nav.special') }}</p>
      <h1>{{ t('home.deals_of_day') }}</h1>
      <p class="sub">{{ t('deal.page_sub') }}</p>
    </header>

    <div v-if="status === 'loading'" class="grid">
      <div v-for="i in 2" :key="i" class="sk" />
    </div>
    <div v-else-if="status === 'error'" class="state">
      <p>{{ t('catalog.load_error') }}</p>
      <button class="link" @click="load">{{ t('common.retry') }}</button>
    </div>
    <div v-else-if="!deals.length" class="state">
      <p>{{ t('deal.none') }}</p>
      <RouterLink class="cta" :to="{ name: 'catalog' }">{{ t('cart.browse') }}</RouterLink>
    </div>
    <div v-else class="grid">
      <DealCard v-for="d in deals" :key="d.id" :deal="d" />
    </div>
  </main>
</template>

<style scoped>
.dealspage {
  max-width: 1320px;
  margin: 0 auto;
  padding: clamp(1.5rem, 4vw, 3rem) clamp(1rem, 4vw, 2.5rem) clamp(3rem, 7vw, 5rem);
}
.head {
  text-align: center;
  margin-bottom: clamp(1.5rem, 3.5vw, 2.5rem);
}
.eyebrow {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--accent-text);
  font-weight: 700;
}
.head h1 {
  font-family: var(--font-display);
  font-size: clamp(1.6rem, 3.2vw, 2.4rem);
  font-weight: 800;
  margin: 8px 0 6px;
}
.sub {
  color: var(--text-muted);
  font-size: 14px;
  margin: 0;
}
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}
.sk {
  min-height: 260px;
  border-radius: var(--radius-lg);
  background: var(--surface-2);
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  50% {
    opacity: 0.55;
  }
}
.state {
  text-align: center;
  padding: 48px 0;
  color: var(--text-muted);
}
.link {
  border: 0;
  background: none;
  color: var(--accent-text);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  text-decoration: underline;
}
.cta {
  display: inline-block;
  margin-top: 10px;
  background: var(--accent);
  color: var(--on-accent);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  text-decoration: none;
  padding: 12px 24px;
  border-radius: var(--radius-full);
}
@media (min-width: 640px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
