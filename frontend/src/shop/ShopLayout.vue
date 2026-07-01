<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useCart } from "./cart";
import { theme, toggleTheme } from "../lib/theme";

const { count, refresh } = useCart();
const router = useRouter();
const q = ref("");

onMounted(refresh);

function search() {
  router.push({ name: "catalog", query: q.value ? { q: q.value } : {} });
}
</script>

<template>
  <div class="shop">
    <div class="util">
      <div class="wrap util__in">
        <span>Welcome to the Arvel Electronics Store</span>
        <nav class="util__nav">
          <RouterLink to="/account">My Account</RouterLink><i>·</i>
          <RouterLink to="/account">Wishlist</RouterLink><i>·</i>
          <RouterLink to="/cart">Checkout</RouterLink><i>·</i>
          <button class="util__theme" @click="toggleTheme" :aria-label="`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`">
            {{ theme === "dark" ? "☀ Light" : "☾ Dark" }}
          </button>
        </nav>
      </div>
    </div>

    <header class="head">
      <div class="wrap head__in">
        <RouterLink to="/" class="logo">Arvel<span>.</span>Shop</RouterLink>
        <form class="search" @submit.prevent="search">
          <span class="search__cat">All Categories ▾</span>
          <input v-model="q" placeholder="Search the entire store here…" aria-label="Search products" />
          <button class="search__go" type="submit">Search</button>
        </form>
        <div class="hicons">
          <RouterLink to="/account" class="hic">
            <svg viewBox="0 0 24 24" class="ic"><circle cx="12" cy="8" r="3.4"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>
            <span>Account</span>
          </RouterLink>
          <RouterLink to="/cart" class="hic hic--cart">
            <svg viewBox="0 0 24 24" class="ic"><path d="M3 3h2l2 12h11l2-8H6"/><circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/></svg>
            <span>Cart</span>
            <b v-if="count" class="n">{{ count }}</b>
          </RouterLink>
        </div>
      </div>
    </header>

    <nav class="deptbar">
      <div class="wrap deptbar__in">
        <span class="deptbar__all"><svg viewBox="0 0 24 24" class="ic ic--sm"><path d="M4 6h16M4 12h16M4 18h16"/></svg> Shop by Department</span>
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/">Promotions</RouterLink>
        <RouterLink to="/account">Track Your Order</RouterLink>
        <RouterLink to="/">Support</RouterLink>
      </div>
    </nav>

    <main class="wrap main"><RouterView /></main>

    <footer class="foot">
      <div class="wrap foot__in">
        <div>
          <div class="logo logo--foot">Arvel<span>.</span>Shop</div>
          <p>Worldwide electronics, delivered. Built on the arvel framework.</p>
        </div>
        <div><b>Departments</b><a>Computers</a><a>Phones &amp; Tablets</a><a>Cameras</a><a>Audio</a></div>
        <div><b>Service</b><a>Track order</a><a>Returns</a><a>Support</a><a>Contact</a></div>
        <div><b>Company</b><a>About</a><a>Promotions</a><a>Careers</a><a>Privacy</a></div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.shop { min-height: 100vh; display: flex; flex-direction: column; background: var(--canvas); }
.wrap { max-width: var(--container-max); margin: 0 auto; width: 100%; padding: 0 var(--container-pad); }
.ic { width: 22px; height: 22px; stroke: currentColor; fill: none; stroke-width: 1.8; }
.ic--sm { width: 18px; height: 18px; }
.logo { font-family: var(--font-display); font-weight: 800; font-size: 26px; letter-spacing: -.03em; color: var(--text); text-decoration: none; }
.logo span { color: var(--accent); }

.util { background: var(--side-bg); color: var(--side-text); font-size: 12.5px; }
.util__in { display: flex; align-items: center; justify-content: space-between; height: 38px; }
.util__nav { display: flex; align-items: center; gap: 10px; }
.util__nav a { color: var(--side-text); text-decoration: none; opacity: .9; }
.util__nav i { opacity: .3; }
.util__theme { background: none; border: 0; color: var(--side-text); cursor: pointer; font: inherit; opacity: .9; }

.head { background: var(--surface); border-bottom: 1px solid var(--border); }
.head__in { display: flex; align-items: center; gap: 22px; height: 76px; }
.search { flex: 1; display: flex; align-items: center; background: var(--surface-2); border: 1px solid var(--border-2); border-radius: var(--radius-md); height: 46px; overflow: hidden; }
.search__cat { padding: 0 14px; border-right: 1px solid var(--border-2); color: var(--text-muted); font-size: 13px; font-weight: 600; white-space: nowrap; }
.search input { flex: 1; border: 0; background: transparent; padding: 0 14px; font: inherit; color: var(--text); outline: none; }
.search__go { height: 46px; padding: 0 22px; background: var(--accent); color: var(--on-accent); border: 0; font-weight: 700; cursor: pointer; }
.hicons { display: flex; align-items: center; gap: 20px; }
.hic { display: flex; flex-direction: column; align-items: center; gap: 3px; font-size: 11px; color: var(--text-muted); text-decoration: none; position: relative; }
.hic:hover { color: var(--text); }
.hic .n { position: absolute; top: -6px; right: 6px; background: var(--accent); color: var(--on-accent); font-size: 10px; font-weight: 700; border-radius: 999px; min-width: 16px; height: 16px; display: grid; place-items: center; padding: 0 4px; }

.deptbar { background: var(--surface); border-bottom: 1px solid var(--border); }
.deptbar__in { display: flex; align-items: center; gap: 6px; height: 48px; font-size: 13.5px; font-weight: 600; }
.deptbar__all { background: var(--ink-900); color: #fff; height: 48px; display: flex; align-items: center; gap: 10px; padding: 0 18px; border-radius: var(--radius-md) var(--radius-md) 0 0; }
.deptbar a { color: var(--text-muted); text-decoration: none; padding: 0 14px; height: 48px; display: flex; align-items: center; }
.deptbar a:hover { color: var(--text); }

.main { flex: 1; padding: 22px var(--container-pad) 44px; }

.foot { margin-top: auto; background: var(--side-bg); color: var(--side-text); padding: 30px 0; font-size: 12.5px; }
.foot__in { display: flex; justify-content: space-between; gap: 30px; }
.logo--foot { color: #fff; font-size: 20px; }
.foot p { opacity: .7; margin: 10px 0 0; max-width: 220px; }
.foot b { color: #fff; display: block; margin-bottom: 10px; font-size: 13px; }
.foot a { display: block; opacity: .85; padding: 3px 0; text-decoration: none; color: var(--side-text); }
@media (max-width: 860px) { .search__cat { display: none; } .hic span { display: none; } .foot__in { flex-wrap: wrap; } }
</style>
