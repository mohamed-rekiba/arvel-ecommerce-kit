<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Tag from "primevue/tag";
import { onMounted, ref } from "vue";
import { ApiError, type AdminReview, api } from "../api";

const reviews = ref<AdminReview[]>([]);
const loading = ref(true);
const notice = ref<string | null>(null);
const status = ref<"pending" | "approved" | "rejected">("pending");

async function load() {
  loading.value = true;
  notice.value = null;
  try {
    reviews.value = await api.adminReviews(status.value);
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? "You may not moderate reviews." : "Failed to load.";
  } finally {
    loading.value = false;
  }
}

async function decide(review: AdminReview, decision: "approve" | "reject") {
  notice.value = null;
  try {
    await api.moderateReview(review.id, decision);
    await load();
  } catch {
    notice.value = "Moderation failed.";
  }
}

function setStatus(next: typeof status.value) {
  status.value = next;
  void load();
}

onMounted(load);
</script>

<template>
  <section class="page">
    <header class="head">
      <div>
        <p class="eyebrow">Content</p>
        <h1>Reviews</h1>
        <p class="sub">Customer reviews go live only after approval.</p>
      </div>
      <div class="filters">
        <Button
          v-for="s in ['pending', 'approved', 'rejected'] as const"
          :key="s"
          :label="s"
          size="small"
          :severity="status === s ? undefined : 'secondary'"
          :outlined="status !== s"
          @click="setStatus(s)"
        />
      </div>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="reviews" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty><p class="empty">Nothing {{ status }}.</p></template>
        <Column header="Product">
          <template #body="{ data }"><span class="pslug">/{{ data.product_slug }}</span></template>
        </Column>
        <Column header="Review">
          <template #body="{ data }">
            <div class="pname">{{ "★".repeat(data.rating) }} {{ data.title ?? "" }}</div>
            <div class="body">{{ data.body }}</div>
            <div class="pslug">by {{ data.author }}</div>
          </template>
        </Column>
        <Column header="Status" style="width: 7rem">
          <template #body="{ data }">
            <Tag :value="data.status" :severity="data.status === 'approved' ? 'success' : data.status === 'rejected' ? 'danger' : 'warn'" />
          </template>
        </Column>
        <Column header="" style="width: 11rem">
          <template #body="{ data }">
            <Button
              v-if="data.status !== 'approved'"
              label="Approve"
              size="small"
              severity="success"
              outlined
              @click="decide(data, 'approve')"
            />
            <Button
              v-if="data.status !== 'rejected'"
              label="Reject"
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
.head { display: flex; justify-content: space-between; align-items: start; margin-bottom: var(--space-6); }
.filters { display: flex; gap: var(--space-2); }
.panel { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); }
.notice { color: var(--color-danger); margin-bottom: var(--space-4); }
.pname { font-weight: 600; }
.body { font-size: var(--text-sm); margin: var(--space-1) 0; }
.pslug { font-size: var(--text-xs); color: var(--color-text-muted); }
.empty { padding: var(--space-4); color: var(--color-text-muted); }
</style>
