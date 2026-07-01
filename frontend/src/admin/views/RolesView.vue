<script setup lang="ts">
import { onMounted, ref } from "vue";
import { type Role, ApiError, api } from "../api";

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
        ? "You need the roles.manage permission to view roles."
        : "Failed to load roles.";
  }
}
onMounted(load);
</script>

<template>
  <section>
    <header class="page">
      <h1>Roles &amp; permissions</h1>
      <p class="page__sub">What each back-office role is allowed to do. super-admin bypasses every check.</p>
    </header>

    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div v-if="status === 'loading'" class="muted">Loading…</div>
    <div v-else-if="status === 'ready'" class="roles">
      <article v-for="role in roles" :key="role.id" class="role">
        <div class="role__head">
          <h2>{{ role.name }}</h2>
          <span class="badge badge--muted">{{ role.permissions.length || "all" }}</span>
        </div>
        <ul v-if="role.permissions.length" class="perms">
          <li v-for="p in role.permissions" :key="p"><code>{{ p }}</code></li>
        </ul>
        <p v-else class="bypass"><span class="badge badge--ok"><span class="badge__dot" />bypass</span> grants everything</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.page { margin-bottom: var(--space-6); }
.page h1 { font-size: var(--text-2xl); }
.page__sub { color: var(--color-text-muted); margin: var(--space-1) 0 0; }
.notice { background: var(--color-danger-soft); color: var(--color-danger); padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); font-size: var(--text-sm); }
.roles { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-4); }
.role { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-5); box-shadow: var(--shadow-1); }
.role__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-4); }
.role__head h2 { font-size: var(--text-base); text-transform: capitalize; }
.perms { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.perms code { font-family: ui-monospace, monospace; font-size: var(--text-xs); color: var(--color-text-muted); background: var(--color-surface); padding: 3px var(--space-2); border-radius: var(--radius-sm); }
.bypass { font-size: var(--text-sm); color: var(--color-text-muted); display: flex; align-items: center; gap: var(--space-2); }
.muted { color: var(--color-text-muted); }
</style>
