<script setup lang="ts">
import { currentLocale } from '../../lib/i18n'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import { onMounted, ref } from 'vue'
import { type NewsletterSubscriber, ApiError, api } from '../api'
import { t } from '../locale'

const rows = ref<NewsletterSubscriber[]>([])
const loading = ref(true)
const notice = ref<string | null>(null)

async function load() {
  loading.value = true
  try {
    rows.value = await api.newsletter()
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('common.no_catalog') : t('common.load_error')
  } finally {
    loading.value = false
  }
}

function exportCsv() {
  const header = 'email,locale,subscribed_at'
  const lines = rows.value.map((r) => `${r.email},${r.locale},${r.created_at ?? ''}`)
  const blob = new Blob([[header, ...lines].join('\n')], {
    type: 'text/csv;charset=utf-8'
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'newsletter-subscribers.csv'
  a.click()
  URL.revokeObjectURL(url)
}

function fmtDate(iso: string | null): string {
  return iso ? new Date(iso).toLocaleDateString(currentLocale()) : '—'
}

onMounted(load)
</script>

<template>
  <section class="page">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('newsletter.eyebrow') }}</p>
        <h1>{{ t('nav.newsletter') }}</h1>
        <p class="sub">{{ t('newsletter.sub') }}</p>
      </div>
      <Button
        :label="t('newsletter.export')"
        icon="pi pi-download"
        outlined
        :disabled="!rows.length"
        @click="exportCsv"
      />
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable
        :value="rows"
        :loading="loading"
        paginator
        :rows="15"
        data-key="id"
        size="small"
        striped-rows
      >
        <template #empty
          ><p class="empty">{{ t('newsletter.none') }}</p></template
        >
        <Column :header="t('newsletter.email')">
          <template #body="{ data }"
            ><span class="mono">{{ data.email }}</span></template
          >
        </Column>
        <Column :header="t('newsletter.locale')" style="width: 7rem">
          <template #body="{ data }"
            ><span class="loc">{{ data.locale }}</span></template
          >
        </Column>
        <Column :header="t('newsletter.date')" style="width: 11rem">
          <template #body="{ data }">{{ fmtDate(data.created_at) }}</template>
        </Column>
      </DataTable>
    </div>
  </section>
</template>

<style scoped>
.eyebrow {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--accent);
  font-weight: 600;
}
.head {
  margin-bottom: 20px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.head h1 {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 6px 0 2px;
}
.sub {
  color: var(--text-muted);
  font-size: 13px;
  margin: 0;
}
.notice {
  background: var(--danger-bg);
  color: var(--danger-fg);
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 13px;
  margin-bottom: 16px;
}
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-1);
  overflow: hidden;
}
.mono {
  font-family: var(--font-mono);
  font-size: 12.5px;
}
.loc {
  text-transform: uppercase;
  font-size: 11.5px;
  font-weight: 700;
  color: var(--text-muted);
}
.empty {
  text-align: center;
  color: var(--text-subtle);
  padding: 24px 0;
}
</style>
