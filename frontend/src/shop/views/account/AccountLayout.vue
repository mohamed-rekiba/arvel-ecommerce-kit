<script setup lang="ts">
// Guests get the sign-in / register pane instead of the sidebar + child routes.
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError } from '../../api'
import { useAuth } from '../../auth'
import { useCart } from '../../cart'
import { useWishlist } from '../../wishlist'
import { t } from '../../locale'

const { state, restore, login, register, logout } = useAuth()
const wishlist = useWishlist()
const cart = useCart()
const router = useRouter()

const mode = ref<'login' | 'register'>('login')
const name = ref('')
const email = ref('')
const password = ref('')
const error = ref<string | null>(null)
const busy = ref(false)
const restoring = ref(true)

async function submit() {
  busy.value = true
  error.value = null
  try {
    if (mode.value === 'login') await login(email.value, password.value)
    else await register(name.value, email.value, password.value)
    // the guest cart (if any) was merged server-side — refresh so the badge shows it
    await Promise.all([wishlist.refresh(), cart.refresh()])
  } catch (e) {
    error.value =
      e instanceof ApiError && e.status === 401
        ? t('account.bad_credentials')
        : e instanceof ApiError && e.status === 422
          ? t('account.check_details')
          : t('common.error_retry')
  } finally {
    busy.value = false
  }
}

async function signOut() {
  await logout()
  router.push('/')
}

const MENU = [
  {
    to: '/account/profile',
    label: 'account.menu_profile',
    icon: 'M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 2c-4 0-7 2-7 4.5V20h14v-1.5C19 16 16 14 12 14Z'
  },
  {
    to: '/account/orders',
    label: 'account.menu_orders',
    icon: 'M6 4h12l1 4H5zM5 8h14v12H5zM9 12h6'
  },
  {
    to: '/account/addresses',
    label: 'account.menu_addresses',
    icon: 'M12 21s-7-5.5-7-11a7 7 0 0 1 14 0c0 5.5-7 11-7 11Zm0-8.5A2.5 2.5 0 1 0 12 7a2.5 2.5 0 0 0 0 5.5Z'
  },
  {
    to: '/account/wishlist',
    label: 'account.menu_wishlist',
    icon: 'M12 20s-7.5-4.9-9.4-9A5.3 5.3 0 0 1 12 6.4 5.3 5.3 0 0 1 21.4 11c-1.9 4.1-9.4 9-9.4 9Z'
  },
  {
    to: '/account/security',
    label: 'account.menu_security',
    icon: 'M7 10V7a5 5 0 0 1 10 0v3M5 10h14v10H5zM12 14v3'
  },
  {
    to: '/account/notifications',
    label: 'account.menu_notifications',
    icon: 'M6 16v-5a6 6 0 0 1 12 0v5l2 2H4zM10 20a2 2 0 0 0 4 0'
  }
] as const

onMounted(async () => {
  await restore()
  restoring.value = false
})
</script>

<template>
  <div class="acct">
    <!-- breadcrumb page band -->
    <div class="band">
      <div class="band__in">
        <h1>{{ t('account.breadcrumb') }}</h1>
        <nav class="crumbs" :aria-label="t('a11y.breadcrumb')">
          <RouterLink to="/">{{ t('nav.home') }}</RouterLink>
          <span aria-hidden="true">/</span>
          <span>{{ t('account.breadcrumb') }}</span>
        </nav>
      </div>
    </div>

    <div v-if="restoring" class="wrap">
      <p class="muted">{{ t('common.loading') }}</p>
    </div>

    <!-- signed in: sidebar + pane -->
    <div v-else-if="state.customer" class="wrap grid">
      <aside class="side">
        <div class="side__who">
          <span class="side__avatar">
            <img v-if="state.customer.avatar_url" :src="state.customer.avatar_url" alt="" />
            <svg v-else viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="8" r="3.4" />
              <path d="M5 20a7 7 0 0 1 14 0" />
            </svg>
          </span>
          <div class="side__meta">
            <b>{{ state.customer.name }}</b>
            <i>{{ state.customer.email }}</i>
          </div>
        </div>
        <nav class="side__nav" :aria-label="t('account.breadcrumb')">
          <RouterLink v-for="m in MENU" :key="m.to" :to="m.to" class="side__a" active-class="on">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path :d="m.icon" />
            </svg>
            <span>{{ t(m.label) }}</span>
          </RouterLink>
          <button class="side__a side__a--out" @click="signOut">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M9 4h-4v16h4M14 8l4 4-4 4M18 12H8" />
            </svg>
            <span>{{ t('account.sign_out') }}</span>
          </button>
        </nav>
      </aside>
      <section class="pane">
        <RouterView />
      </section>
    </div>

    <!-- signed out: auth pane -->
    <div v-else class="wrap auth">
      <h2>
        {{ mode === 'login' ? t('account.sign_in') : t('account.create') }}
      </h2>
      <p class="auth__sub">
        {{ mode === 'login' ? t('account.login_sub') : t('account.register_sub') }}
      </p>
      <form class="form" @submit.prevent="submit">
        <label v-if="mode === 'register'" class="field">
          <span>{{ t('account.name') }}</span>
          <input v-model="name" type="text" autocomplete="name" required />
        </label>
        <label class="field">
          <span>{{ t('account.email') }}</span>
          <input v-model="email" type="email" autocomplete="email" required />
        </label>
        <label class="field">
          <span>{{ t('account.password') }}</span>
          <input
            v-model="password"
            type="password"
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            required
          />
        </label>
        <p v-if="mode === 'login'" class="forgot">
          <RouterLink to="/forgot-password">{{ t('account.forgot') }}</RouterLink>
        </p>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="cta" :disabled="busy" type="submit">
          {{
            busy
              ? t('common.wait')
              : mode === 'login'
                ? t('account.sign_in')
                : t('account.create_btn')
          }}
        </button>
      </form>
      <p class="switch">
        <template v-if="mode === 'login'">
          {{ t('account.new_here') }}
          <button class="link" @click="mode = 'register'">
            {{ t('account.create') }}
          </button>
        </template>
        <template v-else>
          {{ t('account.have_account') }}
          <button class="link" @click="mode = 'login'">
            {{ t('account.sign_in') }}
          </button>
        </template>
      </p>
    </div>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 1320px;
  margin: 0 auto;
  padding: clamp(1rem, 3vw, 2rem) clamp(1rem, 4vw, 2.5rem) clamp(3rem, 6vw, 5rem);
}

/* page band */
.band {
  background: var(--band);
  border-block: 1px solid var(--border);
}
.band__in {
  max-width: 1320px;
  margin: 0 auto;
  padding: clamp(1.1rem, 3vw, 1.9rem) clamp(1rem, 4vw, 2.5rem);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.band__in h1 {
  font-family: var(--font-display);
  font-size: clamp(1.35rem, 3vw, 1.8rem);
  font-weight: 800;
}
.crumbs {
  display: flex;
  gap: 8px;
  font-size: 12.5px;
  color: var(--text-subtle);
}
.crumbs a {
  color: var(--text-muted);
  text-decoration: none;
}
.crumbs a:hover {
  color: var(--accent-text);
}

/* layout: chip scroller on phone, sidebar >=1024 */
.grid {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.side__who {
  display: none;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  border-bottom: 0;
}
.side__avatar {
  width: 52px;
  height: 52px;
  border-radius: 999px;
  overflow: hidden;
  background: var(--surface-2);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.side__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.side__avatar svg {
  width: 26px;
  height: 26px;
  stroke: var(--text-subtle);
  fill: none;
  stroke-width: 1.6;
}
.side__meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.side__meta b {
  font-size: 14px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.side__meta i {
  font-style: normal;
  font-size: 12px;
  color: var(--text-subtle);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.side__nav {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  scrollbar-width: none;
  padding-block: 2px;
}
.side__nav::-webkit-scrollbar {
  display: none;
}
.side__a {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
}
.side__a svg {
  width: 17px;
  height: 17px;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.7;
  flex-shrink: 0;
}
.side__a.on {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--on-accent);
}
.side__a--out {
  color: var(--sale);
}
.pane {
  min-width: 0;
}

@media (min-width: 1024px) {
  .grid {
    display: grid;
    grid-template-columns: 280px 1fr;
    align-items: start;
    gap: 24px;
  }
  .side__who {
    display: flex;
  }
  .side__nav {
    flex-direction: column;
    gap: 0;
    overflow: visible;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0 0 var(--radius-md) var(--radius-md);
    padding: 6px;
  }
  .side__a {
    border: 0;
    border-radius: var(--radius-sm);
    background: none;
    padding: 11px 12px;
    font-size: 13.5px;
  }
  .side__a.on {
    background: color-mix(in srgb, var(--accent) 12%, transparent);
    color: var(--accent-text);
  }
  .side__a:hover:not(.on) {
    background: var(--surface-2);
  }
}

/* auth pane */
.auth {
  max-width: 480px;
}
.auth h2 {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 800;
  margin-bottom: 4px;
}
.auth__sub {
  color: var(--text-muted);
  font-size: 14px;
  margin-bottom: 22px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field span {
  font-size: 13px;
  font-weight: 600;
}
.field input {
  padding: 11px 14px;
  border: 1px solid var(--border-2);
  border-radius: var(--radius-sm);
  background: var(--bg);
  color: var(--text);
  font: inherit;
}
.field input:focus {
  outline: none;
  border-color: var(--accent);
}
.error {
  color: var(--sale);
  font-size: 13px;
  margin: 0;
}
.forgot {
  font-size: 13px;
  margin: -6px 0 0;
}
.forgot a {
  color: var(--accent-text);
}
.cta {
  padding: 13px;
  border: 0;
  border-radius: var(--radius-full);
  background: var(--accent);
  color: var(--on-accent);
  font-size: 13.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
}
.cta:disabled {
  opacity: 0.6;
}
.switch {
  margin-top: 18px;
  color: var(--text-muted);
  font-size: 13.5px;
}
.link {
  border: none;
  background: none;
  padding: 0;
  color: var(--accent-text);
  font: inherit;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.muted {
  color: var(--text-subtle);
}
</style>
