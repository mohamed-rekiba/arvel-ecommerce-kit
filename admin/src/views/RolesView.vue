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
    <h1>Roles &amp; permissions</h1>
    <p v-if="notice" class="notice" role="alert">{{ notice }}</p>

    <div v-if="status === 'loading'" class="muted">Loading…</div>
    <div v-else-if="status === 'ready'" class="roles">
      <article v-for="role in roles" :key="role.id" class="role">
        <h2>{{ role.name }}</h2>
        <ul v-if="role.permissions.length" class="perms">
          <li v-for="p in role.permissions" :key="p">{{ p }}</li>
        </ul>
        <p v-else class="muted">Bypass — grants everything (super-admin).</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
h1 { font-size: var(--text-2xl); margin-bottom: var(--space-4); }
.notice { color: var(--color-danger, #b00020); font-size: var(--text-sm); }
.roles { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-4); }
.role { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-4); }
.role h2 { font-size: var(--text-base); margin: 0 0 var(--space-2); }
.perms { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.perms li { font-size: var(--text-xs); font-family: var(--font-mono, monospace); color: var(--color-text-muted); }
.muted { color: var(--color-text-muted); font-size: var(--text-sm); }
</style>
