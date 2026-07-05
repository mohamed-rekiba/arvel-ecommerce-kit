<script setup lang="ts">
// The single full-page editor shell every admin entity editor uses, so create/edit
// across products, categories, coupons, deals, banners and vendors read as one screen.
// No <form> wrapper — cards own their own inputs (variants/gallery have their own
// actions), and the save bar emits `save` instead of submitting.
import Button from 'primevue/button'
import { t } from '../locale'

defineProps<{
  title: string
  backTo: string
  backLabel: string
  saveLabel: string
  saving?: boolean
  disabled?: boolean
}>()
defineEmits<{ save: [] }>()
</script>

<template>
  <section class="apage">
    <header class="ehead">
      <RouterLink :to="backTo" class="eback">
        <i class="pi pi-arrow-left" /> {{ backLabel }}
      </RouterLink>
      <div class="ehead__row">
        <h1>{{ title }}</h1>
        <slot name="badges" />
      </div>
    </header>

    <slot />

    <div class="ebar">
      <RouterLink :to="backTo">
        <Button type="button" :label="t('common.cancel')" severity="secondary" text />
      </RouterLink>
      <Button
        type="button"
        :label="saveLabel"
        icon="pi pi-check"
        :loading="saving"
        :disabled="disabled"
        @click="$emit('save')"
      />
    </div>
  </section>
</template>
