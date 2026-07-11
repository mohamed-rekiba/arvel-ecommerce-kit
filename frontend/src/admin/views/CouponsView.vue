<script setup lang="ts">
// Only one coupon reaches the storefront's orange bar — the newest live one with announce=true wins.
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError, api, formatPrice } from '../api'
import type { AdminCouponOut } from '../../api/gen/models'
import { t } from '../locale'

const router = useRouter()
const coupons = ref<AdminCouponOut[]>([])
const loading = ref(true)
const notice = ref<string | null>(null)
const q = ref('')

const filtered = computed(() => {
  const term = q.value.trim().toLowerCase()
  if (!term) return coupons.value
  return coupons.value.filter((c) => c.code.toLowerCase().includes(term))
})

async function load() {
  loading.value = true
  notice.value = null
  try {
    coupons.value = await api.adminCoupons()
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t('common.no_catalog') : t('common.load_error')
  } finally {
    loading.value = false
  }
}

async function patch(coupon: AdminCouponOut, body: { active?: boolean; announce?: boolean }) {
  try {
    const updated = await api.updateCoupon(coupon.id, body)
    coupons.value = coupons.value.map((c) => (c.id === updated.id ? updated : c))
  } catch {
    notice.value = t('common.save_error')
  }
}

onMounted(load)
</script>

<template>
  <section class="apage">
    <header class="head">
      <div>
        <p class="eyebrow">{{ t('nav.catalog') }}</p>
        <h1>{{ t('nav.coupons') }}</h1>
        <p class="sub">{{ t('coupons.sub') }}</p>
      </div>
    </header>

    <div class="toolbar">
      <span class="search">
        <i class="pi pi-search" />
        <InputText v-model="q" :placeholder="t('coupons.search_ph')" />
      </span>
      <Button
        class="add"
        :label="t('coupons.new')"
        icon="pi pi-plus"
        @click="router.push('/admin/coupons/new')"
      />
    </div>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div class="panel">
      <DataTable :value="filtered" :loading="loading" data-key="id" size="small" striped-rows>
        <template #empty>
          <p class="empty">{{ t('coupons.none') }}</p>
        </template>
        <Column :header="t('coupons.code')">
          <template #body="{ data }">
            <code class="code">{{ data.code }}</code>
          </template>
        </Column>
        <Column :header="t('coupons.value')" header-style="width: 7rem">
          <template #body="{ data }">
            <Tag
              :value="
                data.type === 'percent' ? `−${data.value}%` : `−${formatPrice(data.value)}`
              "
              severity="warn"
            />
          </template>
        </Column>
        <Column :header="t('coupons.uses')" header-style="width: 6rem">
          <template #body="{ data }">
            <span class="muted"
              >{{ data.uses }}{{ data.usage_limit ? ` / ${data.usage_limit}` : '' }}</span
            >
          </template>
        </Column>
        <Column :header="t('coupons.active')" header-style="width: 6rem">
          <template #body="{ data }">
            <ToggleSwitch
              :model-value="data.active"
              :aria-label="t('coupons.active')"
              @update:model-value="patch(data, { active: !data.active })"
            />
          </template>
        </Column>
        <Column :header="t('coupons.announce')" header-style="width: 7rem">
          <template #body="{ data }">
            <ToggleSwitch
              :model-value="data.announce"
              :aria-label="t('coupons.announce')"
              @update:model-value="patch(data, { announce: !data.announce })"
            />
          </template>
        </Column>
        <Column header="" header-style="width: 4rem">
          <template #body="{ data }">
            <Button
              icon="pi pi-pencil"
              text
              rounded
              :aria-label="t('common.edit')"
              @click="router.push(`/admin/coupons/${data.id}`)"
            />
          </template>
        </Column>
      </DataTable>
    </div>
  </section>
</template>

<style scoped>
.code {
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 700;
}
</style>
