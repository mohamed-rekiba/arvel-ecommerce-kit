<script setup lang="ts">
// Manage Address (profile ref 1): saved-address cards with a single-default rule + an inline
// add/edit form. Checkout consumes these by id (A2).
import { onMounted, reactive, ref } from "vue";
import {
  ApiError,
  type CountryCode,
  SHIPPING_COUNTRY_CODES,
  type SavedAddress,
  api,
} from "../../api";
import { t } from "../../locale";

const list = ref<SavedAddress[]>([]);
const loading = ref(true);
const formOpen = ref(false);
const editing = ref<number | null>(null);
const error = ref<string | null>(null);

const blank = () => ({
  label: "",
  name: "",
  line1: "",
  line2: "",
  city: "",
  postal_code: "",
  country: "US" as CountryCode,
  phone: "",
  is_default: false,
});
const form = reactive(blank());

async function load() {
  loading.value = true;
  try {
    list.value = await api.addresses();
  } finally {
    loading.value = false;
  }
}

function openAdd() {
  Object.assign(form, blank());
  editing.value = null;
  error.value = null;
  formOpen.value = true;
}

function openEdit(a: SavedAddress) {
  Object.assign(form, {
    label: a.label ?? "",
    name: a.name,
    line1: a.line1,
    line2: a.line2 ?? "",
    city: a.city,
    postal_code: a.postal_code,
    country: a.country as CountryCode,
    phone: a.phone ?? "",
    is_default: a.is_default,
  });
  editing.value = a.id;
  error.value = null;
  formOpen.value = true;
}

async function save() {
  error.value = null;
  const payload = {
    label: form.label || null,
    name: form.name,
    line1: form.line1,
    line2: form.line2 || null,
    city: form.city,
    postal_code: form.postal_code,
    country: form.country,
    phone: form.phone || null,
    is_default: form.is_default,
  };
  try {
    if (editing.value === null) await api.createAddress(payload);
    else await api.updateAddress(editing.value, payload);
    formOpen.value = false;
    await load();
  } catch (e) {
    error.value =
      e instanceof ApiError && e.status === 422
        ? Object.values(e.errors)[0]?.[0] ?? t("account.check_details_short")
        : t("common.error_retry");
  }
}

async function setDefault(a: SavedAddress) {
  await api.updateAddress(a.id, {
    label: a.label,
    name: a.name,
    line1: a.line1,
    line2: a.line2,
    city: a.city,
    postal_code: a.postal_code,
    country: a.country as CountryCode,
    phone: a.phone,
    is_default: true,
  });
  await load();
}

async function remove(a: SavedAddress) {
  if (!window.confirm(t("account.addr_delete_confirm"))) return;
  await api.deleteAddress(a.id);
  await load();
}

onMounted(load);
</script>

<template>
  <div class="card">
    <div class="head">
      <h2 class="card__title">{{ t("account.menu_addresses") }}</h2>
      <button v-if="!formOpen" class="cta cta--sm" @click="openAdd">+ {{ t("account.addr_add") }}</button>
    </div>

    <form v-if="formOpen" class="form" @submit.prevent="save">
      <h3 class="form__title">{{ editing === null ? t("account.addr_add") : t("account.addr_edit") }}</h3>
      <label class="field">
        <span>{{ t("account.addr_label") }} <em>{{ t("common.optional") }}</em></span>
        <input v-model.trim="form.label" type="text" :placeholder="t('account.addr_label_ph')" />
      </label>
      <label class="field">
        <span>{{ t("account.name") }}</span>
        <input v-model.trim="form.name" type="text" autocomplete="name" required />
      </label>
      <label class="field field--wide">
        <span>{{ t("account.addr_line1") }}</span>
        <input v-model.trim="form.line1" type="text" autocomplete="address-line1" required />
      </label>
      <label class="field field--wide">
        <span>{{ t("account.addr_line2") }} <em>{{ t("common.optional") }}</em></span>
        <input v-model.trim="form.line2" type="text" autocomplete="address-line2" />
      </label>
      <label class="field">
        <span>{{ t("account.addr_city") }}</span>
        <input v-model.trim="form.city" type="text" autocomplete="address-level2" required />
      </label>
      <label class="field">
        <span>{{ t("account.addr_postal") }}</span>
        <input v-model.trim="form.postal_code" type="text" autocomplete="postal-code" required />
      </label>
      <label class="field">
        <span>{{ t("account.addr_country") }}</span>
        <select v-model="form.country">
          <option v-for="c in SHIPPING_COUNTRY_CODES" :key="c" :value="c">{{ c }}</option>
        </select>
      </label>
      <label class="field">
        <span>{{ t("account.phone") }} <em>{{ t("common.optional") }}</em></span>
        <input v-model.trim="form.phone" type="tel" autocomplete="tel" />
      </label>
      <label class="check field--wide">
        <input v-model="form.is_default" type="checkbox" />
        <span>{{ t("account.addr_default") }}</span>
      </label>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <div class="form__actions field--wide">
        <button class="cta" type="submit">{{ t("account.addr_save") }}</button>
        <button class="ghost" type="button" @click="formOpen = false">{{ t("account.addr_cancel") }}</button>
      </div>
    </form>

    <p v-if="loading" class="muted">{{ t("common.loading") }}</p>
    <p v-else-if="!list.length && !formOpen" class="muted">{{ t("account.addr_empty") }}</p>

    <ul v-if="list.length" class="grid">
      <li v-for="a in list" :key="a.id" class="addr" :class="{ 'addr--default': a.is_default }">
        <div class="addr__top">
          <b>{{ a.label || a.name }}</b>
          <span v-if="a.is_default" class="badge">{{ t("account.addr_default_badge") }}</span>
        </div>
        <p class="addr__body">
          {{ a.name }}<br />
          {{ a.line1 }}<template v-if="a.line2">, {{ a.line2 }}</template><br />
          {{ a.city }}, {{ a.postal_code }} — {{ a.country }}
          <template v-if="a.phone"><br /><span dir="ltr">{{ a.phone }}</span></template>
        </p>
        <div class="addr__actions">
          <button class="mini" @click="openEdit(a)">{{ t("account.addr_edit") }}</button>
          <button v-if="!a.is_default" class="mini" @click="setDefault(a)">{{ t("account.addr_set_default") }}</button>
          <button class="mini mini--danger" @click="remove(a)">{{ t("account.addr_delete") }}</button>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: clamp(1rem, 3vw, 1.75rem); }
.head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 18px; }
.card__title { font-family: var(--font-display); font-size: 1.15rem; font-weight: 800; }
.muted { color: var(--text-subtle); }

.form { display: grid; grid-template-columns: 1fr; gap: 13px; margin-bottom: 22px; padding: 16px; border: 1px dashed var(--border-2); border-radius: var(--radius-md); }
.form__title { grid-column: 1 / -1; font-size: 14px; font-weight: 700; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field span { font-size: 13px; font-weight: 600; }
.field em { color: var(--text-subtle); font-style: normal; font-size: 11.5px; }
.field input, .field select { padding: 10px 13px; border: 1px solid var(--border-2); border-radius: var(--radius-sm); background: var(--bg); color: var(--text); font: inherit; }
.field input:focus, .field select:focus { outline: none; border-color: var(--accent); }
.check { display: flex; align-items: center; gap: 9px; font-size: 13.5px; }
.check input { accent-color: var(--accent); width: 16px; height: 16px; }
.error { grid-column: 1 / -1; color: var(--sale); font-size: 13px; margin: 0; }
.form__actions { display: flex; gap: 10px; }
.cta { padding: 11px 22px; border: 0; border-radius: var(--radius-full); background: var(--accent); color: var(--on-accent); font-size: 12.5px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; cursor: pointer; }
.cta--sm { padding: 9px 16px; }
.ghost { padding: 11px 22px; border: 1px solid var(--border-2); border-radius: var(--radius-full); background: none; color: var(--text-muted); font-size: 12.5px; font-weight: 700; cursor: pointer; }

.grid { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: 1fr; gap: 12px; }
.addr { border: 1px solid var(--border); border-radius: var(--radius-md); padding: 14px; display: flex; flex-direction: column; gap: 8px; }
.addr--default { border-color: var(--accent); }
.addr__top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.addr__top b { font-size: 14px; font-weight: 700; }
.badge { background: color-mix(in srgb, var(--accent) 12%, transparent); color: var(--accent-text); font-size: 10.5px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; padding: 3px 9px; border-radius: var(--radius-full); }
.addr__body { font-size: 13px; color: var(--text-muted); line-height: 1.55; margin: 0; }
.addr__actions { display: flex; flex-wrap: wrap; gap: 7px; margin-top: auto; }
.mini { padding: 6px 12px; border: 1px solid var(--border-2); border-radius: var(--radius-full); background: none; color: var(--text); font-size: 12px; font-weight: 600; cursor: pointer; }
.mini:hover { border-color: var(--accent); color: var(--accent-text); }
.mini--danger { color: var(--sale); }
.mini--danger:hover { border-color: var(--sale); color: var(--sale); }

@media (min-width: 640px) {
  .form { grid-template-columns: 1fr 1fr; }
  .field--wide { grid-column: 1 / -1; }
  .grid { grid-template-columns: 1fr 1fr; }
}
</style>
