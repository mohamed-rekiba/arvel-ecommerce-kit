<script setup lang="ts">
import Tag from "primevue/tag";
import { onMounted, ref } from "vue";
import { type Role, ApiError, api } from "../api";
import { t } from "../locale";

const roles = ref<Role[]>([]);
const status = ref<"loading" | "error" | "ready">("loading");
const notice = ref<string | null>(null);

async function load() {
  status.value = "loading";
  try {
    roles.value = await api.roles();
    status.value = "ready";
  } catch (e) {
    status.value = "error";
    notice.value =
      e instanceof ApiError && e.status === 403
        ? t("roles.no_view")
        : t("roles.load_error");
  }
}
onMounted(load);
</script>

<template>
  <section class="page">
    <header class="head">
      <p class="eyebrow">{{ t("nav.system") }}</p>
      <h1>{{ t("nav.roles") }}</h1>
      <p class="sub">{{ t("roles.sub") }}</p>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div v-if="status === 'loading'" class="muted">{{ t("common.loading") }}</div>
    <div v-else-if="status === 'ready'" class="roles">
      <article v-for="role in roles" :key="role.id" class="role">
        <div class="role__head">
          <h2>{{ role.name }}</h2>
          <Tag
            :value="role.permissions.length ? t('roles.perms', { n: role.permissions.length }) : t('roles.bypass')"
            :severity="role.permissions.length ? 'secondary' : 'success'"
          />
        </div>
        <ul v-if="role.permissions.length" class="perms">
          <li v-for="p in role.permissions" :key="p"><code>{{ p }}</code></li>
        </ul>
        <p v-else class="bypass">{{ t("roles.bypass_note") }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: .16em; color: var(--accent); font-weight: 600; }
.head { margin-bottom: 20px; }
.head h1 { font-family: var(--font-display); font-size: 26px; font-weight: 700; letter-spacing: -.02em; margin: 6px 0 2px; }
.sub { color: var(--text-muted); font-size: 13px; margin: 0; }
.notice { background: var(--danger-bg); color: var(--danger-fg); padding: 10px 14px; border-radius: var(--radius-md); font-size: 13px; }
.roles { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
.role { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 18px; box-shadow: var(--shadow-1); }
.role__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.role__head h2 { font-family: var(--font-display); font-size: 15px; font-weight: 700; text-transform: capitalize; }
.perms { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.perms code { font-family: var(--font-mono); font-size: 11.5px; color: var(--text-muted); background: var(--surface-2); padding: 3px 8px; border-radius: var(--radius-sm); }
.bypass { font-size: 13px; color: var(--text-muted); margin: 0; }
.muted { color: var(--text-muted); }
</style>
