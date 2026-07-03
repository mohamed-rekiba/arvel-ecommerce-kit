<script setup lang="ts">
// Personal info (profile ref 1): avatar with camera-edit overlay + name/email/phone form +
// the email-verification nudge. The avatar posts multipart to /api/account/avatar (arvel
// HasMedia on User — replace-on-upload).
import { onMounted, ref } from "vue";
import { ApiError, api } from "../../api";
import { useAuth } from "../../auth";
import { t } from "../../locale";

const { state } = useAuth();

const profile = ref({ name: "", email: "", phone: "" });
const profileMsg = ref<string | null>(null);
const profileErr = ref<string | null>(null);
const resent = ref(false);
const photoBusy = ref(false);
const photoMsg = ref<string | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);

function syncForm() {
  if (!state.customer) return;
  profile.value = {
    name: state.customer.name,
    email: state.customer.email,
    phone: state.customer.phone ?? "",
  };
}

async function saveProfile() {
  profileMsg.value = null;
  profileErr.value = null;
  try {
    state.customer = await api.updateProfile({
      name: profile.value.name,
      email: profile.value.email,
      phone: profile.value.phone,
    });
    syncForm();
    profileMsg.value = state.customer.email_verified
      ? t("account.profile_saved")
      : t("account.profile_saved_verify");
  } catch (e) {
    profileErr.value =
      e instanceof ApiError && e.status === 422
        ? Object.values(e.errors)[0]?.[0] ?? t("account.check_details_short")
        : t("account.profile_error");
  }
}

async function onPhoto(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  photoBusy.value = true;
  photoMsg.value = null;
  try {
    state.customer = await api.uploadAvatar(file);
    photoMsg.value = t("account.photo_updated");
  } catch {
    photoMsg.value = t("account.photo_error");
  } finally {
    photoBusy.value = false;
    if (fileInput.value) fileInput.value.value = "";
  }
}

async function resendVerification() {
  await api.resendVerification();
  resent.value = true;
}

onMounted(syncForm);
</script>

<template>
  <div v-if="state.customer" class="card">
    <h2 class="card__title">{{ t("account.menu_profile") }}</h2>

    <div class="ava">
      <span class="ava__img">
        <img v-if="state.customer.avatar_url" :src="state.customer.avatar_url" alt="" />
        <svg v-else viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3.4" /><path d="M5 20a7 7 0 0 1 14 0" /></svg>
        <button class="ava__edit" :disabled="photoBusy" :aria-label="t('account.change_photo')" @click="fileInput?.click()">
          <svg viewBox="0 0 24 24"><path d="M4 8h3l2-2h6l2 2h3v11H4zM12 17a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Z" /></svg>
        </button>
        <input ref="fileInput" type="file" accept="image/*" class="sr" @change="onPhoto" />
      </span>
      <div class="ava__meta">
        <b>{{ state.customer.name }}</b>
        <i>
          {{ state.customer.email }}
          <span v-if="state.customer.email_verified" class="ok-badge">✓ {{ t("account.verified") }}</span>
        </i>
        <p v-if="photoMsg" class="mini" role="status">{{ photoMsg }}</p>
      </div>
    </div>

    <p v-if="!state.customer.email_verified" class="verify" role="status">
      {{ t("account.not_verified") }}
      <button v-if="!resent" class="link" @click="resendVerification">{{ t("account.resend") }}</button>
      <span v-else>{{ t("account.verification_sent") }}</span>
    </p>

    <form class="form" @submit.prevent="saveProfile">
      <label class="field">
        <span>{{ t("account.name") }}</span>
        <input v-model.trim="profile.name" type="text" autocomplete="name" required />
      </label>
      <label class="field">
        <span>{{ t("account.email") }}</span>
        <input v-model.trim="profile.email" type="email" autocomplete="email" required />
      </label>
      <label class="field field--wide">
        <span>{{ t("account.phone") }} <em>{{ t("account.phone_hint") }}</em></span>
        <input v-model.trim="profile.phone" type="tel" autocomplete="tel" />
      </label>
      <p v-if="profileErr" class="error" role="alert">{{ profileErr }}</p>
      <p v-if="profileMsg" class="okmsg" role="status">{{ profileMsg }}</p>
      <div class="actions">
        <button class="cta" type="submit">{{ t("account.save_profile") }}</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: clamp(1rem, 3vw, 1.75rem); }
.card__title { font-family: var(--font-display); font-size: 1.15rem; font-weight: 800; margin-bottom: 18px; }

.ava { display: flex; align-items: center; gap: 16px; margin-bottom: 18px; }
.ava__img { position: relative; width: 84px; height: 84px; border-radius: 999px; background: var(--surface-2); display: grid; place-items: center; flex-shrink: 0; }
.ava__img img { width: 100%; height: 100%; border-radius: 999px; object-fit: cover; }
.ava__img svg { width: 38px; height: 38px; stroke: var(--text-subtle); fill: none; stroke-width: 1.5; }
.ava__edit { position: absolute; bottom: 0; inset-inline-end: 0; width: 30px; height: 30px; border-radius: 999px; border: 2px solid var(--surface); background: var(--accent); color: var(--on-accent); display: grid; place-items: center; cursor: pointer; }
.ava__edit svg { width: 15px; height: 15px; stroke: currentColor; fill: none; stroke-width: 1.7; }
.ava__edit:disabled { opacity: .6; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
.ava__meta { min-width: 0; }
.ava__meta b { font-size: 16px; font-weight: 700; display: block; }
.ava__meta i { font-style: normal; font-size: 13px; color: var(--text-muted); }
.ok-badge { color: var(--success-fg); font-size: 11.5px; font-weight: 700; margin-inline-start: 6px; }
.mini { font-size: 12px; color: var(--accent-text); margin-top: 4px; }

.verify { background: var(--warn-bg); color: var(--warn-fg); border-radius: var(--radius-sm); padding: 10px 14px; font-size: 13px; margin-bottom: 18px; }
.verify .link { color: inherit; }

.form { display: grid; grid-template-columns: 1fr; gap: 14px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field span { font-size: 13px; font-weight: 600; }
.field em { color: var(--text-subtle); font-style: normal; font-size: 11.5px; }
.field input { padding: 11px 14px; border: 1px solid var(--border-2); border-radius: var(--radius-sm); background: var(--bg); color: var(--text); font: inherit; }
.field input:focus { outline: none; border-color: var(--accent); }
.error { color: var(--sale); font-size: 13px; margin: 0; }
.okmsg { color: var(--success-fg); font-size: 13px; margin: 0; }
.actions { display: flex; }
.cta { padding: 12px 26px; border: 0; border-radius: var(--radius-full); background: var(--accent); color: var(--on-accent); font-size: 13px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; cursor: pointer; }
.link { border: none; background: none; padding: 0; font: inherit; cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }

@media (min-width: 640px) {
  .form { grid-template-columns: 1fr 1fr; }
  .field--wide, .error, .okmsg, .actions { grid-column: 1 / -1; }
}
</style>
