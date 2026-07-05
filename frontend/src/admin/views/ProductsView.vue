<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { type AdminProduct, ApiError, api, name } from '../api'
import { type MessageKey, t } from '../locale'

const router = useRouter()

const products = ref<AdminProduct[]>([])
const status = ref<'loading' | 'error' | 'ready'>('loading')
const notice = ref<string | null>(null)
const showArchived = ref(false)

async function load() {
  status.value = 'loading'
  try {
    products.value = (await api.products(1, showArchived.value)).data
    status.value = 'ready'
  } catch (e) {
    status.value = 'error'
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('common.no_catalog') : t('products.load_error')
  }
}

async function remove(p: AdminProduct) {
  if (!window.confirm(t('products.archive_confirm', { name: name(p) }))) return
  notice.value = null
  try {
    await api.deleteProduct(p.id)
    await load()
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 404
        ? t('products.no_archive')
        : t('products.archive_error')
  }
}

async function restore(p: AdminProduct) {
  notice.value = null
  try {
    await api.restoreProduct(p.id)
    await load()
  } catch {
    notice.value = t('products.restore_error')
  }
}

async function toggleArchived() {
  showArchived.value = !showArchived.value
  await load()
}
onMounted(load)
</script>

<template>
  <section class="page">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('nav.catalog') }}</p>
        <h1>{{ t('nav.products') }}</h1>
        <p class="sub">{{ t('products.sub') }}</p>
      </div>
      <div class="head__actions">
        <Button
          :label="showArchived ? t('products.active') : t('products.archived')"
          severity="secondary"
          outlined
          @click="toggleArchived"
        />
        <Button
          :label="t('products.new')"
          icon="pi pi-plus"
          @click="router.push('/admin/products/new')"
        />
      </div>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable
        :value="products"
        :loading="status === 'loading'"
        paginator
        :rows="10"
        data-key="id"
        size="small"
        striped-rows
      >
        <template #empty
          ><p class="empty">{{ t('products.none') }}</p></template
        >
        <Column :header="t('products.product')">
          <template #body="{ data }">
            <RouterLink class="plink" :to="`/admin/products/${data.id}`">
              <div class="pname">{{ name(data) }}</div>
              <div class="pslug">/{{ data.slug }}</div>
            </RouterLink>
          </template>
        </Column>
        <Column :header="t('common.status')">
          <template #body="{ data }">
            <Tag
              :value="t(`pstatus.${data.status}` as MessageKey)"
              :severity="data.status === 'active' ? 'success' : 'secondary'"
            />
          </template>
        </Column>
        <Column :header="t('products.storefront')">
          <template #body="{ data }">
            <Tag
              :value="data.is_visible ? t('products.visible') : t('products.hidden')"
              :severity="data.is_visible ? 'success' : 'secondary'"
            />
          </template>
        </Column>
        <Column header="" style="width: 9rem">
          <template #body="{ data }">
            <template v-if="showArchived">
              <Button :label="t('products.restore')" size="small" outlined @click="restore(data)" />
            </template>
            <template v-else>
              <Button
                icon="pi pi-pencil"
                text
                rounded
                :aria-label="t('common.edit')"
                @click="router.push(`/admin/products/${data.id}`)"
              />
              <Button
                icon="pi pi-trash"
                text
                rounded
                severity="danger"
                :aria-label="t('products.archive')"
                @click="remove(data)"
              />
            </template>
          </template>
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
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
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
.create {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 14px;
  box-shadow: var(--shadow-1);
}
.create .grow {
  flex: 1;
}
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-1);
  overflow: hidden;
}
.pname {
  font-weight: 600;
  font-size: 13.5px;
}
.pslug {
  color: var(--text-subtle);
  font-size: 11.5px;
}
.empty {
  text-align: center;
  color: var(--text-subtle);
  padding: 24px 0;
}
.plink {
  text-decoration: none;
  color: inherit;
  display: block;
}
.plink:hover .pname {
  text-decoration: underline;
}
.head__actions {
  display: flex;
  gap: var(--space-2);
}
</style>
