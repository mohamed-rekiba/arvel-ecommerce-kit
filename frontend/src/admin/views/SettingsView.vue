<script setup lang="ts">
// Store settings (retires the "SOON" tile): the cache-backed KV pairs the storefront reads —
// contact email/phone, topbar welcome line, free-shipping threshold. Saves invalidate the
// server cache, so the storefront reflects an edit on the next load.
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import { onMounted, reactive, ref } from "vue";
import { ApiError, api } from "../api";
import { t } from "../locale";

const values = reactive<Record<string, string>>({
  "store.email": "",
  "store.phone": "",
  "store.welcome": "",
  "store.free_shipping_over": "",
});
const loading = ref(true);
const saving = ref(false);
const notice = ref<string | null>(null);
const saved = ref(false);

async function load() {
  loading.value = true;
  try {
    const res = await api.adminSettings();
    for (const key of Object.keys(values)) values[key] = res.values[key] ?? "";
  } catch (e) {
    notice.value =
      e instanceof ApiError && e.status === 403 ? t("common.no_catalog") : t("common.load_error");
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  notice.value = null;
  saved.value = false;
  try {
    const res = await api.updateSettings({ ...values });
    for (const key of Object.keys(values)) values[key] = res.values[key] ?? "";
    saved.value = true;
  } catch (e) {
    notice.value =
      e instanceof ApiError
        ? Object.values(e.errors)[0]?.[0] ?? t("common.save_error")
        : t("common.save_error");
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="page">
    <header class="head">
      <p class="eyebrow">{{ t("settings.eyebrow") }}</p>
      <h1>{{ t("nav.settings") }}</h1>
      <p class="sub">{{ t("settings.sub") }}</p>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>
    <p v-if="saved" class="ok" role="status">{{ t("settings.saved") }}</p>

    <form class="panel form" @submit.prevent="save">
      <label class="field">
        <span>{{ t("settings.store_email") }}</span>
        <InputText v-model="values['store.email']" type="email" :disabled="loading" />
        <small>{{ t("settings.store_email_hint") }}</small>
      </label>
      <label class="field">
        <span>{{ t("settings.store_phone") }}</span>
        <InputText v-model="values['store.phone']" :disabled="loading" />
      </label>
      <label class="field field--wide">
        <span>{{ t("settings.welcome") }}</span>
        <InputText v-model="values['store.welcome']" :disabled="loading" />
        <small>{{ t("settings.welcome_hint") }}</small>
      </label>
      <label class="field">
        <span>{{ t("settings.free_ship") }}</span>
        <InputText v-model="values['store.free_shipping_over']" inputmode="numeric" :disabled="loading" />
        <small>{{ t("settings.free_ship_hint") }}</small>
      </label>
      <div class="actions field--wide">
        <Button type="submit" :label="t('settings.save')" :loading="saving" :disabled="loading" />
      </div>
    </form>
  </section>
</template>

<style scoped>
.eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: .16em; color: var(--accent); font-weight: 600; }
.head { margin-bottom: 20px; }
.head h1 { font-family: var(--font-display); font-size: 26px; font-weight: 700; letter-spacing: -.02em; margin: 6px 0 2px; }
.sub { color: var(--text-muted); font-size: 13px; margin: 0; }
.notice { background: var(--danger-bg); color: var(--danger-fg); padding: 10px 14px; border-radius: var(--radius-md); font-size: 13px; margin-bottom: 16px; }
.ok { background: var(--success-bg); color: var(--success-fg); padding: 10px 14px; border-radius: var(--radius-md); font-size: 13px; margin-bottom: 16px; }

.panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 22px; }
.form { display: grid; grid-template-columns: 1fr; gap: 16px; max-width: 720px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field span { font-size: 13px; font-weight: 600; }
.field small { color: var(--text-subtle); font-size: 11.5px; }
.actions { display: flex; }
@media (min-width: 720px) {
  .form { grid-template-columns: 1fr 1fr; }
  .field--wide { grid-column: 1 / -1; }
}
</style>
