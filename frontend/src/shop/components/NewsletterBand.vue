<script setup lang="ts">
import { ref } from "vue";
import { api } from "../api";
import { t } from "../locale";

const email = ref("");
const state = ref<"idle" | "busy" | "done" | "error">("idle");

async function subscribe() {
  if (!email.value.trim()) return;
  state.value = "busy";
  try {
    await api.subscribeNewsletter(email.value);
    state.value = "done";
    email.value = "";
  } catch {
    state.value = "error";
  }
}
</script>

<template>
  <section class="nl">
    <div class="nl__in">
      <div class="nl__copy">
        <h2>{{ t("newsletter.title") }}</h2>
        <p>{{ t("newsletter.sub") }}</p>
      </div>
      <form class="nl__form" @submit.prevent="subscribe">
        <input
          v-model.trim="email"
          type="email"
          :placeholder="t('newsletter.ph')"
          :aria-label="t('newsletter.ph')"
          required
        />
        <button type="submit" :disabled="state === 'busy'">{{ t("newsletter.cta") }}</button>
      </form>
      <p v-if="state === 'done'" class="nl__msg nl__msg--ok" role="status">{{ t("newsletter.done") }}</p>
      <p v-else-if="state === 'error'" class="nl__msg nl__msg--err" role="alert">{{ t("newsletter.error") }}</p>
    </div>
  </section>
</template>

<style scoped>
.nl { background: var(--nav-bg); }
.nl__in { max-width: 1320px; margin: 0 auto; padding: clamp(1.75rem, 4vw, 2.75rem) clamp(1rem, 4vw, 2.5rem); display: grid; grid-template-columns: 1fr; gap: 16px; align-items: center; }
.nl__copy h2 { font-family: var(--font-display); font-size: clamp(1.15rem, 2.5vw, 1.5rem); font-weight: 800; color: var(--nav-text-hi); }
.nl__copy p { margin: 4px 0 0; font-size: 13.5px; color: var(--nav-text); }
.nl__form { display: flex; gap: 8px; }
.nl__form input { flex: 1; min-width: 0; padding: 12px 16px; border: 1px solid color-mix(in srgb, var(--nav-text) 30%, transparent); border-radius: var(--radius-full); background: color-mix(in srgb, var(--nav-text-hi) 8%, transparent); color: var(--nav-text-hi); font: inherit; font-size: 13.5px; }
.nl__form input::placeholder { color: var(--nav-text); }
.nl__form input:focus { outline: none; border-color: var(--accent-bright); }
.nl__form button { padding: 12px 24px; border: 0; border-radius: var(--radius-full); background: var(--accent-bright); color: var(--on-accent-bright); font-size: 12.5px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; cursor: pointer; white-space: nowrap; }
.nl__form button:disabled { opacity: .6; }
.nl__msg { font-size: 13px; margin: 0; }
.nl__msg--ok { color: var(--nav-text-hi); }
.nl__msg--err { color: var(--accent-bright); }

@media (min-width: 1024px) {
  .nl__in { grid-template-columns: 1fr auto; column-gap: 40px; }
  .nl__form { min-width: 420px; }
  .nl__msg { grid-column: 2; }
}
</style>
