<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'
import { onMounted, ref } from 'vue'
import { ApiError, type AdminReview, api } from '../api'
import { type MessageKey, t } from '../locale'

const reviews = ref<AdminReview[]>([])
const loading = ref(true)
const notice = ref<string | null>(null)
const status = ref<'pending' | 'approved' | 'rejected'>('pending')

async function load() {
  loading.value = true
  notice.value = null
  try {
    reviews.value = await api.adminReviews(status.value)
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('reviews.no_moderate') : t('common.load_error')
  } finally {
    loading.value = false
  }
}

async function decide(review: AdminReview, decision: 'approve' | 'reject') {
  notice.value = null
  try {
    await api.moderateReview(review.id, decision)
    await load()
  } catch {
    notice.value = t('reviews.moderation_error')
  }
}

function setStatus(next: typeof status.value) {
  status.value = next
  void load()
}

onMounted(load)
</script>

<template>
  <section class="apage">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('reviews.eyebrow') }}</p>
        <h1>{{ t('nav.reviews') }}</h1>
        <p class="sub">{{ t('reviews.sub') }}</p>
      </div>
    </header>

    <div class="toolbar">
      <div class="segs" role="group" :aria-label="t('common.status')">
        <button
          v-for="s in ['pending', 'approved', 'rejected'] as const"
          :key="s"
          class="seg"
          :class="{ on: status === s }"
          @click="setStatus(s)"
        >
          {{ t(`review.${s}` as MessageKey) }}
        </button>
      </div>
    </div>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="reviews" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty>
          <p class="empty">
            {{ t('reviews.none', { status: t(`review.${status}` as MessageKey) }) }}
          </p>
        </template>
        <Column :header="t('products.product')">
          <template #body="{ data }">
            <span class="pslug">/{{ data.product_slug }}</span>
          </template>
        </Column>
        <Column :header="t('reviews.review')">
          <template #body="{ data }">
            <div class="stars">
              {{ '★'.repeat(data.rating) }}<span class="pname"> {{ data.title ?? '' }}</span>
            </div>
            <div class="body">{{ data.body }}</div>
            <div class="pslug">{{ t('reviews.by', { author: data.author }) }}</div>
          </template>
        </Column>
        <Column :header="t('common.status')" header-style="width: 7rem">
          <template #body="{ data }">
            <Tag
              :value="t(`review.${data.status}` as MessageKey)"
              :severity="
                data.status === 'approved'
                  ? 'success'
                  : data.status === 'rejected'
                    ? 'danger'
                    : 'warn'
              "
            />
          </template>
        </Column>
        <Column header="" header-style="width: 11rem">
          <template #body="{ data }">
            <Button
              v-if="data.status !== 'approved'"
              :label="t('reviews.approve')"
              size="small"
              severity="success"
              outlined
              @click="decide(data, 'approve')"
            />
            <Button
              v-if="data.status !== 'rejected'"
              :label="t('reviews.reject')"
              size="small"
              severity="danger"
              text
              @click="decide(data, 'reject')"
            />
          </template>
        </Column>
      </DataTable>
    </div>
  </section>
</template>

<style scoped>
.segs {
  display: inline-flex;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 3px;
}
.seg {
  border: 0;
  background: none;
  border-radius: 999px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
}
.seg.on {
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow-1);
}
.stars {
  font-weight: 600;
  color: var(--star);
}
.body {
  font-size: 13px;
  color: var(--text-muted);
  margin: 3px 0;
}
</style>
