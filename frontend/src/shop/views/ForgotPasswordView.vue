<script setup lang="ts">
import { ref } from "vue";
import { api } from "../api";
import { t } from "../locale";

const email = ref("");
const sent = ref(false);
const busy = ref(false);

async function submit() {
  busy.value = true;
  try {
    await api.forgotPassword(email.value);
  } finally {
    // identical outcome whether or not the email exists — no enumeration
    sent.value = true;
    busy.value = false;
  }
}
</script>

<template>
  <main class="narrow">
    <div v-if="sent" class="state">
      <h1>{{ t("auth.check_inbox") }}</h1>
      <p class="muted">{{ t("auth.reset_sent") }}</p>
      <RouterLink class="btn btn--primary" to="/account">{{ t("auth.back_signin") }}</RouterLink>
    </div>
    <template v-else>
      <h1>{{ t("account.forgot") }}</h1>
      <p class="muted">{{ t("auth.forgot_sub") }}</p>
      <form class="form" @submit.prevent="submit">
        <label class="field">
          <span>{{ t("account.email") }}</span>
          <input v-model.trim="email" type="email" autocomplete="email" required />
        </label>
        <button class="btn btn--primary" type="submit" :disabled="busy">
          {{ busy ? t("pdp.sending") : t("auth.send_reset") }}
        </button>
      </form>
    </template>
  </main>
</template>

<style scoped>
.narrow { max-width: 420px; margin: 0 auto; padding: var(--space-16) var(--container-pad); }
h1 { font-size: var(--text-3xl); margin-bottom: var(--space-2); }
.muted { color: var(--color-text-muted); margin-bottom: var(--space-6); }
.form .field { display: block; margin-bottom: var(--space-4); }
.field span { display: block; font-size: var(--text-sm); margin-bottom: var(--space-1); }
.field input { width: 100%; padding: var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); color: var(--color-text); font: inherit; }
.state { text-align: center; padding: var(--space-8) 0; }
</style>
