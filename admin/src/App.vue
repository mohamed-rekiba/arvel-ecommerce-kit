<script setup lang="ts">
import { onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuth } from "./auth";

const { state, restore, logout } = useAuth();
const router = useRouter();
const route = useRoute();

onMounted(restore);

function signOut() {
  logout();
  router.push("/login");
}
</script>

<template>
  <div v-if="route.meta.public">
    <RouterView />
  </div>
  <div v-else class="shell">
    <aside class="sidebar">
      <div class="sidebar__brand">arvel <span>admin</span></div>
      <nav class="sidebar__nav" aria-label="Admin">
        <RouterLink to="/products">Products</RouterLink>
        <RouterLink to="/roles">Roles</RouterLink>
        <RouterLink to="/audit">Audit log</RouterLink>
      </nav>
      <div class="sidebar__foot">
        <span v-if="state.user" class="sidebar__user">{{ state.user.email }}</span>
        <button class="linkbtn" @click="signOut">Sign out</button>
      </div>
    </aside>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.shell { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }
.sidebar { display: flex; flex-direction: column; border-right: 1px solid var(--color-border); padding: var(--space-5); background: var(--color-surface); }
.sidebar__brand { font-weight: var(--weight-semibold); font-size: var(--text-lg); margin-bottom: var(--space-6); }
.sidebar__brand span { color: var(--color-accent); }
.sidebar__nav { display: flex; flex-direction: column; gap: var(--space-1); }
.sidebar__nav a { padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); text-decoration: none; color: var(--color-text-muted); }
.sidebar__nav a:hover { background: var(--color-bg); color: var(--color-text); }
.sidebar__nav a.router-link-active { background: var(--color-accent); color: var(--color-text-inverse); }
.sidebar__foot { margin-top: auto; padding-top: var(--space-6); font-size: var(--text-sm); color: var(--color-text-muted); }
.sidebar__user { display: block; margin-bottom: var(--space-2); overflow: hidden; text-overflow: ellipsis; }
.linkbtn { border: none; background: none; color: var(--color-accent); cursor: pointer; padding: 0; font: inherit; }
.content { padding: var(--space-8); max-width: 1000px; }
</style>
