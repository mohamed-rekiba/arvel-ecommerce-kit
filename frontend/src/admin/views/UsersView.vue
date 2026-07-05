<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { onMounted, ref } from 'vue'
import { ApiError, type AdminUser, type AdminUserDetail, api, formatPrice } from '../api'
import { t } from '../locale'

const users = ref<AdminUser[]>([])
const loading = ref(true)
const notice = ref<string | null>(null)
const q = ref('')

const detail = ref<AdminUserDetail | null>(null)
const detailOpen = ref(false)
const roleOptions = ref<string[]>([])
const newRole = ref<string | null>(null)
const roleError = ref<string | null>(null)

async function load() {
  loading.value = true
  notice.value = null
  try {
    users.value = (await api.adminUsers(q.value)).data
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('users.no_browse') : t('common.load_error')
  } finally {
    loading.value = false
  }
}

async function open(user: AdminUser) {
  roleError.value = null
  try {
    detail.value = await api.adminUserDetail(user.id)
    detailOpen.value = true
    if (roleOptions.value.length === 0) {
      try {
        roleOptions.value = (await api.roles()).map((r) => r.name)
      } catch {
        roleOptions.value = [] // the viewer lacks roles.manage — read-only detail
      }
    }
  } catch {
    notice.value = t('users.load_one_error')
  }
}

async function assign() {
  if (!detail.value || !newRole.value) return
  roleError.value = null
  try {
    await api.assignRole(detail.value.id, newRole.value)
    detail.value = await api.adminUserDetail(detail.value.id)
    newRole.value = null
    await load()
  } catch (e) {
    roleError.value =
      e instanceof ApiError && e.status === 403 ? t('users.no_manage') : t('users.assign_error')
  }
}

async function revoke(role: string) {
  if (!detail.value) return
  roleError.value = null
  try {
    await api.revokeRole(detail.value.id, role)
    detail.value = await api.adminUserDetail(detail.value.id)
    await load()
  } catch (e) {
    roleError.value =
      e instanceof ApiError && e.status === 403 ? t('users.no_manage') : t('users.revoke_error')
  }
}

onMounted(load)
</script>

<template>
  <section class="page">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('users.eyebrow') }}</p>
        <h1>{{ t('nav.users') }}</h1>
        <p class="sub">{{ t('users.sub') }}</p>
      </div>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <form class="search" @submit.prevent="load">
      <InputText v-model="q" :placeholder="t('users.search_ph')" class="grow" />
      <Button type="submit" :label="t('nav.search')" severity="secondary" outlined />
    </form>

    <div class="panel">
      <DataTable :value="users" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty
          ><p class="empty">{{ t('users.none') }}</p></template
        >
        <Column :header="t('users.user')">
          <template #body="{ data }">
            <button class="ulink" @click="open(data)">
              <span class="uava">
                <img v-if="data.avatar_url" :src="data.avatar_url" alt="" />
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="8" r="3.4" />
                  <path d="M5 20a7 7 0 0 1 14 0" />
                </svg>
              </span>
              <span class="umeta">
                <span class="pname">{{ data.name }}</span>
                <span class="pslug">{{ data.email }}</span>
              </span>
            </button>
          </template>
        </Column>
        <Column :header="t('users.verified')">
          <template #body="{ data }">
            <Tag
              :value="data.email_verified ? t('users.verified') : t('users.unverified')"
              :severity="data.email_verified ? 'success' : 'secondary'"
            />
          </template>
        </Column>
        <Column :header="t('users.roles')">
          <template #body="{ data }">
            <span v-if="data.roles.length === 0" class="pslug">{{ t('users.customer') }}</span>
            <Tag v-for="r in data.roles" :key="r" :value="r" class="role-tag" />
          </template>
        </Column>
      </DataTable>
    </div>

    <Dialog
      v-model:visible="detailOpen"
      modal
      :header="detail?.name ?? ''"
      :style="{ width: '26rem' }"
    >
      <template v-if="detail">
        <p class="pslug">
          {{ detail.email }} ·
          {{ detail.email_verified ? t('users.verified_lc') : t('users.unverified_lc') }}
        </p>
        <p class="stat">
          {{ detail.orders_count }}
          {{ detail.orders_count === 1 ? t('users.order_one') : t('users.order_many') }}
          ·
          {{
            t('users.lifetime', {
              total: formatPrice(detail.total_spent_cents)
            })
          }}
        </p>

        <h3>{{ t('users.roles') }}</h3>
        <p v-if="detail.roles.length === 0" class="pslug">
          {{ t('users.no_roles') }}
        </p>
        <ul class="roles">
          <li v-for="r in detail.roles" :key="r">
            <Tag :value="r" />
            <Button
              size="small"
              text
              severity="danger"
              :label="t('users.revoke')"
              @click="revoke(r)"
            />
          </li>
        </ul>
        <div v-if="roleOptions.length" class="assign">
          <Select
            v-model="newRole"
            :options="roleOptions.filter((r) => !detail!.roles.includes(r))"
            :placeholder="t('users.add_role')"
          />
          <Button size="small" :label="t('users.assign')" :disabled="!newRole" @click="assign" />
        </div>
        <p v-if="roleError" class="notice" role="alert">{{ roleError }}</p>
      </template>
    </Dialog>
  </section>
</template>

<style scoped>
.head {
  margin-bottom: var(--space-6);
}
.search {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.search .grow {
  flex: 1;
}
.panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.notice {
  color: var(--color-danger);
  margin: var(--space-3) 0;
}
.ulink {
  background: none;
  border: 0;
  padding: 0;
  text-align: start;
  cursor: pointer;
  font: inherit;
  color: inherit;
  display: block;
}
.ulink:hover .pname {
  text-decoration: underline;
}
.pname {
  font-weight: 600;
  display: block;
}
.ulink {
  display: flex;
  align-items: center;
  gap: 10px;
}
.uava {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  overflow: hidden;
  background: var(--surface-2);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.uava img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.uava svg {
  width: 16px;
  height: 16px;
  stroke: var(--text-subtle);
  fill: none;
  stroke-width: 1.6;
}
.umeta {
  min-width: 0;
  text-align: start;
}
.pslug {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}
.role-tag {
  margin-inline-end: var(--space-1);
}
.stat {
  margin: var(--space-2) 0 var(--space-4);
}
.roles {
  list-style: none;
  margin: 0 0 var(--space-3);
  padding: 0;
}
.roles li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-1) 0;
}
.assign {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
.empty {
  padding: var(--space-4);
  color: var(--color-text-muted);
}
h3 {
  font-size: var(--text-sm);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
  margin: var(--space-4) 0 var(--space-2);
}
</style>
