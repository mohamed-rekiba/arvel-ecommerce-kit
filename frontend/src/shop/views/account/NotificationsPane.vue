<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { type Notification, api } from '../../api'
import { t } from '../../locale'

const notifications = ref<Notification[]>([])
const loading = ref(true)
const unread = computed(() => notifications.value.filter((n) => !n.read).length)

async function load() {
  try {
    notifications.value = await api.notifications()
  } catch {
    notifications.value = []
  } finally {
    loading.value = false
  }
}

async function markAllRead() {
  await api.markNotificationsRead()
  await load()
}

onMounted(load)
</script>

<template>
  <div class="card">
    <div class="head">
      <h2 class="card__title">
        {{ t('account.notifications') }}
        <span v-if="unread" class="badge">{{ unread }}</span>
      </h2>
      <button v-if="unread" class="mark" @click="markAllRead">
        {{ t('account.mark_read') }}
      </button>
    </div>
    <p v-if="loading" class="muted">{{ t('common.loading') }}</p>
    <p v-else-if="!notifications.length" class="muted">
      {{ t('account.notif_empty') }}
    </p>
    <ul v-else class="list">
      <li v-for="n in notifications" :key="n.id" class="note" :class="{ 'note--unread': !n.read }">
        <span v-if="!n.read" class="dot" aria-hidden="true" />
        <span class="msg">{{ n.message }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: clamp(1rem, 3vw, 1.75rem);
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 16px;
}
.card__title {
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  gap: 9px;
}
.badge {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  background: var(--accent-bright);
  color: var(--on-accent-bright);
  border-radius: var(--radius-full);
  font-family: var(--font-text);
  font-size: 11px;
  font-weight: 800;
  display: inline-grid;
  place-items: center;
}
.mark {
  border: none;
  background: none;
  padding: 0;
  color: var(--accent-text);
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.muted {
  color: var(--text-subtle);
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.note {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-top: 1px solid var(--border);
  color: var(--text-muted);
}
.note:first-child {
  border-top: 0;
}
.note--unread {
  color: var(--text);
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent-bright);
  flex-shrink: 0;
}
.msg {
  font-size: 13.5px;
}
</style>
