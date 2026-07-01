<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useCart } from "./cart";
import { theme, toggleTheme } from "../lib/theme";

const { count, refresh } = useCart();
const router = useRouter();
const route = useRoute();
const scrolled = ref(false);

onMounted(() => {
  refresh();
  const onScroll = () => (scrolled.value = window.scrollY > 8);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
});
</script>

<template>
  <div class="shop">
    <header class="hd" :class="{ 'hd--scrolled': scrolled }">
      <div class="hd__in">
        <RouterLink to="/" class="word" aria-label="Arvel home">ARVEL</RouterLink>
        <nav class="nav" aria-label="Primary">
          <RouterLink :to="{ name: 'catalog' }" :class="{ on: route.name === 'catalog' }">Shop</RouterLink>
          <RouterLink to="/">Collections</RouterLink>
          <RouterLink to="/">About</RouterLink>
        </nav>
        <div class="tools">
          <RouterLink :to="{ name: 'catalog' }" class="ic" aria-label="Search">
            <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></svg>
          </RouterLink>
          <button class="ic" @click="toggleTheme" :aria-label="`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`">
            <svg v-if="theme === 'dark'" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4.5" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" /></svg>
            <svg v-else viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" /></svg>
          </button>
          <RouterLink to="/account" class="ic" aria-label="Account">
            <svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="3.4" /><path d="M5 20a7 7 0 0 1 14 0" /></svg>
          </RouterLink>
          <RouterLink to="/cart" class="ic ic--cart" aria-label="Cart">
            <svg viewBox="0 0 24 24"><path d="M6 8h12l-1 12H7z" /><path d="M9 8a3 3 0 0 1 6 0" /></svg>
            <span v-if="count" class="n">{{ count }}</span>
          </RouterLink>
        </div>
      </div>
    </header>

    <main class="main"><RouterView /></main>

    <footer class="ft">
      <div class="ft__top">
        <div class="ft__brand">
          <div class="word word--ft">ARVEL</div>
          <p>Considered electronics. Designed to disappear into your life.</p>
        </div>
        <div class="ft__cols">
          <div><h4>Shop</h4><a>New arrivals</a><a>Audio</a><a>Displays</a><a>Accessories</a></div>
          <div><h4>Support</h4><a>Track order</a><a>Shipping &amp; returns</a><a>Contact</a></div>
          <div><h4>Company</h4><a>About</a><a>Stores</a><a>Journal</a></div>
        </div>
      </div>
      <div class="ft__base">
        <span>© 2026 Arvel — built on the arvel framework.</span>
        <span>Privacy · Terms</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.shop { min-height: 100vh; display: flex; flex-direction: column; background: var(--bg); }

/* header — one quiet row */
.hd { position: sticky; top: 0; z-index: var(--z-header); background: color-mix(in srgb, var(--bg) 86%, transparent); backdrop-filter: saturate(140%) blur(14px); transition: border-color var(--motion-base), background var(--motion-base); border-bottom: 1px solid transparent; }
.hd--scrolled { border-bottom-color: var(--border); }
.hd__in { max-width: 1280px; margin: 0 auto; padding: 0 clamp(1.25rem, 5vw, 3.5rem); height: 76px; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; }
.word { font-family: var(--font-display); font-weight: 700; font-size: 20px; letter-spacing: .34em; color: var(--text); text-decoration: none; }
.nav { display: flex; gap: 34px; justify-self: center; }
.nav a { font-size: 12px; letter-spacing: .12em; text-transform: uppercase; font-weight: 500; color: var(--text-muted); text-decoration: none; transition: color var(--motion-base); }
.nav a:hover, .nav a.on { color: var(--text); }
.tools { display: flex; align-items: center; gap: 6px; justify-self: end; }
.ic { width: 40px; height: 40px; display: grid; place-items: center; border: 0; background: none; color: var(--text-muted); cursor: pointer; border-radius: var(--radius-full); position: relative; text-decoration: none; transition: color var(--motion-base), background var(--motion-base); }
.ic:hover { color: var(--text); background: color-mix(in srgb, var(--text) 6%, transparent); }
.ic svg { width: 19px; height: 19px; stroke: currentColor; fill: none; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }
.ic--cart .n { position: absolute; top: 4px; right: 4px; min-width: 16px; height: 16px; padding: 0 4px; background: var(--accent); color: var(--on-accent); border-radius: 999px; font-size: 10px; font-weight: 700; display: grid; place-items: center; }

.main { flex: 1; }

/* footer — airy, minimal */
.ft { margin-top: clamp(4rem, 10vw, 8rem); border-top: 1px solid var(--border); }
.ft__top { max-width: 1280px; margin: 0 auto; padding: clamp(3rem, 6vw, 5rem) clamp(1.25rem, 5vw, 3.5rem) clamp(2rem, 4vw, 3rem); display: grid; grid-template-columns: 1.4fr 2fr; gap: 40px; }
.word--ft { letter-spacing: .34em; font-size: 18px; margin-bottom: 16px; }
.ft__brand p { color: var(--text-muted); font-size: 14px; max-width: 30ch; line-height: 1.6; }
.ft__cols { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.ft__cols h4 { font-size: 11px; text-transform: uppercase; letter-spacing: .14em; color: var(--text-subtle); margin: 0 0 14px; font-weight: 600; }
.ft__cols a { display: block; font-size: 14px; color: var(--text-muted); text-decoration: none; padding: 5px 0; transition: color var(--motion-base); }
.ft__cols a:hover { color: var(--text); }
.ft__base { max-width: 1280px; margin: 0 auto; padding: 22px clamp(1.25rem, 5vw, 3.5rem); border-top: 1px solid var(--border); display: flex; justify-content: space-between; font-size: 12px; color: var(--text-subtle); }

@media (max-width: 760px) {
  .nav { display: none; }
  .hd__in { grid-template-columns: 1fr auto; }
  .ft__top { grid-template-columns: 1fr; }
  .ft__cols { grid-template-columns: 1fr 1fr; }
}
</style>
