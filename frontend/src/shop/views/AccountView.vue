<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { type Notification, type Order, ApiError, api, formatPrice } from "../api";
import { useAuth } from "../auth";
import { useWishlist } from "../wishlist";
import ProductCard from "../components/ProductCard.vue";

const { state, restore, login, register, logout } = useAuth();
const wishlist = useWishlist();

const mode = ref<"login" | "register">("login");
const name = ref("");
const email = ref("");
const password = ref("");
const error = ref<string | null>(null);
const busy = ref(false);

const orders = ref<Order[]>([]);
const ordersLoading = ref(false);
const notifications = ref<Notification[]>([]);
const unread = computed(() => notifications.value.filter((n) => !n.read).length);

async function loadOrders() {
  ordersLoading.value = true;
  try {
    orders.value = await api.myOrders();
  } catch {
    orders.value = [];
  } finally {
    ordersLoading.value = false;
  }
}

async function loadNotifications() {
  try {
    notifications.value = await api.notifications();
  } catch {
    notifications.value = [];
  }
}

async function markAllRead() {
  await api.markNotificationsRead();
  await loadNotifications();
}

async function submit() {
  busy.value = true;
  error.value = null;
  try {
    if (mode.value === "login") await login(email.value, password.value);
    else await register(name.value, email.value, password.value);
    await Promise.all([loadOrders(), loadNotifications(), wishlist.refresh()]);
  } catch (e) {
    error.value =
      e instanceof ApiError && e.status === 401
        ? "Those credentials don't match."
        : e instanceof ApiError && e.status === 422
          ? "Please check your details and try again."
          : "Something went wrong. Please try again.";
  } finally {
    busy.value = false;
  }
}

async function signOut() {
  await logout();
  orders.value = [];
  notifications.value = [];
}

onMounted(async () => {
  await restore();
  if (state.customer) await Promise.all([loadOrders(), loadNotifications(), wishlist.refresh()]);
});
</script>

<template>
  <main class="account">
    <p class="eyebrow">Your account</p>

    <!-- signed in -->
    <template v-if="state.customer">
      <div class="account__head">
        <h1>Hello, {{ state.customer.name }}</h1>
        <button class="btn" @click="signOut">Sign out</button>
      </div>
      <p class="account__email">{{ state.customer.email }}</p>

      <section v-if="notifications.length" class="notes">
        <div class="notes__head">
          <h2 class="orders__title">
            Notifications
            <span v-if="unread" class="notes__badge">{{ unread }}</span>
          </h2>
          <button v-if="unread" class="notes__mark" @click="markAllRead">Mark all read</button>
        </div>
        <ul class="notes__list">
          <li v-for="n in notifications" :key="n.id" class="note" :class="{ 'note--unread': !n.read }">
            <span v-if="!n.read" class="note__dot" aria-hidden="true" />
            <span class="note__msg">{{ n.message }}</span>
          </li>
        </ul>
      </section>

      <section v-if="wishlist.state.products.length" class="wish">
        <h2 class="orders__title">Wishlist</h2>
        <div class="wish__grid">
          <ProductCard v-for="p in wishlist.state.products" :key="p.id" :product="p" />
        </div>
      </section>

      <section class="orders">
        <h2 class="orders__title">Order history</h2>
        <p v-if="ordersLoading" class="muted">Loading…</p>
        <p v-else-if="orders.length === 0" class="muted">You haven't placed any orders yet.</p>
        <ul v-else class="orders__list">
          <li v-for="o in orders" :key="o.id" class="order">
            <RouterLink class="order__link" :to="`/orders/${o.id}`">
              <div>
                <span class="order__id">Order #{{ o.id }}</span>
                <span class="order__items">{{ o.items.length }} item{{ o.items.length === 1 ? "" : "s" }}</span>
              </div>
              <span class="order__status">{{ o.status }}</span>
              <span class="order__total">{{ formatPrice(o.total_cents) }}</span>
            </RouterLink>
          </li>
        </ul>
      </section>
    </template>

    <!-- signed out -->
    <template v-else>
      <h1>{{ mode === "login" ? "Sign in" : "Create an account" }}</h1>
      <p class="account__sub">
        {{ mode === "login" ? "Access your orders and check out faster." : "Save your details and track every order." }}
      </p>
      <form class="form" @submit.prevent="submit">
        <label v-if="mode === 'register'" class="field">
          <span>Name</span>
          <input v-model="name" type="text" autocomplete="name" required />
        </label>
        <label class="field">
          <span>Email</span>
          <input v-model="email" type="email" autocomplete="email" required />
        </label>
        <label class="field">
          <span>Password</span>
          <input v-model="password" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" required />
        </label>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="btn btn--primary submit" :disabled="busy" type="submit">
          {{ busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account" }}
        </button>
      </form>
      <p class="switch">
        <template v-if="mode === 'login'">
          New here? <button class="link" @click="mode = 'register'">Create an account</button>
        </template>
        <template v-else>
          Already have an account? <button class="link" @click="mode = 'login'">Sign in</button>
        </template>
      </p>
    </template>
  </main>
</template>

<style scoped>
.account { max-width: 480px; margin: 0 auto; padding: var(--space-20) var(--container-pad) 0; }
.account__head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-4); margin: var(--space-2) 0 var(--space-1); }
.account__head h1 { font-size: var(--text-3xl); }
.account__head .btn { white-space: nowrap; flex-shrink: 0; }
.account__email { color: var(--color-text-muted); margin: 0 0 var(--space-10); }
.account h1 { font-size: var(--text-3xl); margin: var(--space-2) 0 var(--space-3); }
.account__sub { color: var(--color-text-muted); margin: 0 0 var(--space-8); }
.form { display: flex; flex-direction: column; gap: var(--space-4); }
.field { display: flex; flex-direction: column; gap: var(--space-2); }
.field span { font-size: var(--text-sm); font-weight: var(--weight-medium); }
.field input { padding: var(--space-3) var(--space-4); border: 1px solid var(--color-border-strong); border-radius: var(--radius-md); background: var(--color-bg); font: inherit; }
.field input:focus { outline: none; border-color: var(--color-text); }
.error { color: var(--color-danger); font-size: var(--text-sm); margin: 0; }
.submit { width: 100%; padding: var(--space-4); margin-top: var(--space-2); }
.switch { margin-top: var(--space-6); color: var(--color-text-muted); font-size: var(--text-sm); }
.link { border: none; background: none; padding: 0; color: var(--color-accent); font: inherit; cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
.orders__title { font-size: var(--text-xl); margin-bottom: var(--space-5); }
.wish { margin-bottom: var(--space-10); }
.wish__grid { display: grid; grid-template-columns: 1fr; gap: var(--space-4); }
@media (min-width: 640px) { .wish__grid { grid-template-columns: repeat(2, 1fr); } }
.notes { margin-bottom: var(--space-10); }
.notes__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-4); }
.notes__head .orders__title { margin-bottom: 0; display: inline-flex; align-items: center; gap: var(--space-3); }
.notes__badge { display: inline-flex; align-items: center; justify-content: center; min-width: 1.4rem; height: 1.4rem; padding: 0 6px; background: var(--color-accent); color: var(--color-text-inverse); border-radius: var(--radius-full); font-family: var(--font-text); font-size: var(--text-xs); font-weight: var(--weight-semibold); }
.notes__mark { border: none; background: none; padding: 0; color: var(--color-accent); font: inherit; font-size: var(--text-sm); cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
.notes__list { list-style: none; margin: 0; padding: 0; }
.note { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3) 0; border-top: 1px solid var(--color-border); color: var(--color-text-muted); }
.note--unread { color: var(--color-text); }
.note__dot { width: 7px; height: 7px; border-radius: 50%; background: var(--color-accent); flex-shrink: 0; }
.note__msg { font-size: var(--text-sm); }
.orders__list { list-style: none; margin: 0; padding: 0; }
.order { display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: var(--space-3); padding: var(--space-4) 0; border-top: 1px solid var(--color-border); }
/* grid items default to min-width:auto (sized to content); without this the flexible first column
   can refuse to shrink below its content's intrinsic width and overflow on a narrow phone. */
.order > div { min-width: 0; }
.order__id { font-family: var(--font-display); font-size: var(--text-lg); margin-right: var(--space-3); }
.order__items { color: var(--color-text-muted); font-size: var(--text-sm); }
.order__status { padding: 2px var(--space-3); background: var(--color-accent-soft); color: var(--color-accent); border-radius: var(--radius-full); font-size: var(--text-xs); text-transform: capitalize; }
.order__total { font-weight: var(--weight-medium); min-width: 4rem; text-align: right; }
.muted { color: var(--color-text-muted); }
</style>
