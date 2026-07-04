<script setup lang="ts">
import { ref } from "vue";
import { ApiError, api } from "../../api";
import { t } from "../../locale";

const currentPassword = ref("");
const newPassword = ref("");
const msg = ref<string | null>(null);
const err = ref<string | null>(null);

async function save() {
  msg.value = null;
  err.value = null;
  try {
    await api.changePassword(currentPassword.value, newPassword.value);
    currentPassword.value = "";
    newPassword.value = "";
    msg.value = t("account.password_updated");
  } catch (e) {
    err.value =
      e instanceof ApiError && e.status === 422
        ? Object.values(e.errors)[0]?.[0] ?? t("account.check_passwords")
        : t("account.password_error");
  }
}
</script>

<template>
  <div class="card">
    <h2 class="card__title">{{ t("account.change_password") }}</h2>
    <form class="form" @submit.prevent="save">
      <label class="field">
        <span>{{ t("account.current_password") }}</span>
        <input v-model="currentPassword" type="password" autocomplete="current-password" required />
      </label>
      <label class="field">
        <span>{{ t("account.new_password") }}</span>
        <input v-model="newPassword" type="password" autocomplete="new-password" minlength="8" required />
      </label>
      <p v-if="err" class="error" role="alert">{{ err }}</p>
      <p v-if="msg" class="okmsg" role="status">{{ msg }}</p>
      <div><button class="cta" type="submit">{{ t("account.update_password") }}</button></div>
    </form>
  </div>
</template>

<style scoped>
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: clamp(1rem, 3vw, 1.75rem); }
.card__title { font-family: var(--font-display); font-size: 1.15rem; font-weight: 800; margin-bottom: 18px; }
.form { display: flex; flex-direction: column; gap: 14px; max-width: 420px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field span { font-size: 13px; font-weight: 600; }
.field input { padding: 11px 14px; border: 1px solid var(--border-2); border-radius: var(--radius-sm); background: var(--bg); color: var(--text); font: inherit; }
.field input:focus { outline: none; border-color: var(--accent); }
.error { color: var(--sale); font-size: 13px; margin: 0; }
.okmsg { color: var(--success-fg); font-size: 13px; margin: 0; }
.cta { padding: 12px 26px; border: 0; border-radius: var(--radius-full); background: var(--accent); color: var(--on-accent); font-size: 13px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; cursor: pointer; }
</style>
