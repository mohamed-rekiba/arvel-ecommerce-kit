<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuth } from "./auth";

const { state, restore, logout } = useAuth();
const router = useRouter();
const route = useRoute();

onMounted(restore);

const nav = [
  { to: "/dashboard", label: "Overview" },
  { to: "/products", label: "Products" },
  { to: "/roles", label: "Roles" },
  { to: "/audit", label: "Audit log" },
];

const initial = computed(() => (state.user?.email ?? "?").charAt(0).toUpperCase());

function signOut() {
  logout();
  router.push("/login");
}
</script>

<template>
  <RouterView v-if="route.meta.public" />
  <div v-else class="shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand__mark" aria-hidden="true" />
        <span class="brand__name">Arvel <span>Console</span></span>
      </div>
      <nav class="nav" aria-label="Admin">
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="nav__item">
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="user">
        <div class="user__avatar" aria-hidden="true">{{ initial }}</div>
        <div class="user__meta">
          <span class="user__email">{{ state.user?.email ?? "…" }}</span>
          <button class="user__signout" @click="signOut">Sign out</button>
        </div>
      </div>
    </aside>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.shell { display: grid; grid-template-columns: 248px 1fr; min-height: 100vh; }
.sidebar { display: flex; flex-direction: column; gap: var(--space-6); padding: var(--space-5); background: var(--color-bg); border-right: 1px solid var(--color-border); }
.brand { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2) var(--space-2) var(--space-4); }
.brand__mark { width: 22px; height: 22px; border-radius: 6px; background: var(--color-accent); position: relative; flex-shrink: 0; }
.brand__mark::after { content: ""; position: absolute; inset: 6px; border: 2px solid var(--color-text-inverse); border-radius: 2px; }
.brand__name { font-weight: var(--weight-semibold); font-size: var(--text-lg); }
.brand__name span { color: var(--color-text-muted); font-weight: var(--weight-regular); }
.nav { display: flex; flex-direction: column; gap: 2px; }
.nav__item { padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); text-decoration: none; color: var(--color-text-muted); font-weight: var(--weight-medium); font-size: var(--text-base); transition: background var(--motion-base) var(--ease), color var(--motion-base) var(--ease); }
.nav__item:hover { background: var(--color-surface); color: var(--color-text); }
.nav__item.router-link-active { background: var(--color-accent-soft); color: var(--color-accent); }
.user { margin-top: auto; display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3); border-top: 1px solid var(--color-border); }
.user__avatar { width: 32px; height: 32px; border-radius: 50%; background: var(--color-accent); color: var(--color-text-inverse); display: grid; place-items: center; font-weight: var(--weight-semibold); font-size: var(--text-sm); flex-shrink: 0; }
.user__meta { display: flex; flex-direction: column; min-width: 0; }
.user__email { font-size: var(--text-xs); color: var(--color-text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user__signout { align-self: flex-start; border: none; background: none; padding: 0; color: var(--color-accent); font: inherit; font-size: var(--text-xs); font-weight: var(--weight-medium); cursor: pointer; }
.content { padding: var(--space-10) var(--space-12); max-width: 1120px; width: 100%; }
</style>
