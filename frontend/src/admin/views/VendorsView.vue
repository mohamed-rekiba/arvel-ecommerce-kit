<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError, type Vendor, api } from '../api'
import { t } from '../locale'

const router = useRouter()
const vendors = ref<Vendor[]>([])
const loading = ref(true)
const notice = ref<string | null>(null)
const q = ref('')

const filtered = computed(() => {
  const term = q.value.trim().toLowerCase()
  if (!term) return vendors.value
  return vendors.value.filter(
    (v) => v.name.toLowerCase().includes(term) || v.slug.toLowerCase().includes(term)
  )
})

async function load() {
  loading.value = true
  try {
    vendors.value = await api.vendors()
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('common.no_catalog') : t('common.load_error')
  } finally {
    loading.value = false
  }
}

async function togglePublished(vendor: Vendor) {
  notice.value = null
  try {
    const updated = await api.updateVendor(vendor.id, {
      published: !vendor.published
    })
    vendors.value = vendors.value.map((v) => (v.id === updated.id ? updated : v))
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('vendors.no_update') : t('vendors.update_error')
    await load()
  }
}

onMounted(load)
</script>

<template>
  <section class="apage">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('nav.catalog') }}</p>
        <h1>{{ t('nav.vendors') }}</h1>
        <p class="sub">{{ t('vendors.sub') }}</p>
      </div>
    </header>

    <div class="toolbar">
      <span class="search">
        <i class="pi pi-search" />
        <InputText v-model="q" :placeholder="t('vendors.search_ph')" />
      </span>
      <Button
        class="add"
        :label="t('vendors.new_title')"
        icon="pi pi-plus"
        @click="router.push('/admin/vendors/new')"
      />
    </div>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="filtered" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty>
          <p class="empty">{{ t('vendors.none') }}</p>
        </template>
        <Column :header="t('vendors.vendor')">
          <template #body="{ data }">
            <div class="prod">
              <div class="thumb"><i class="pi pi-shop" /></div>
              <div>
                <div class="pname">{{ data.name }}</div>
                <div class="pslug">/{{ data.slug }}</div>
              </div>
            </div>
          </template>
        </Column>
        <Column :header="t('common.status')">
          <template #body="{ data }">
            <Tag
              :value="data.published ? t('categories.published') : t('vendors.unpublished')"
              :severity="data.published ? 'success' : 'warn'"
            />
          </template>
        </Column>
        <Column :header="t('categories.published')" header-style="width: 7rem">
          <template #body="{ data }">
            <ToggleSwitch
              :model-value="data.published"
              :aria-label="t('vendors.toggle', { name: data.name })"
              @update:model-value="togglePublished(data)"
            />
          </template>
        </Column>
        <Column header="" header-style="width: 5rem">
          <template #body="{ data }">
            <Button
              icon="pi pi-pencil"
              text
              rounded
              :aria-label="t('common.edit')"
              @click="router.push(`/admin/vendors/${data.id}`)"
            />
          </template>
        </Column>
      </DataTable>
    </div>
  </section>
</template>
