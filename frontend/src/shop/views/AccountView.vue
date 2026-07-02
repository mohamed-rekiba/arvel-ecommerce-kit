<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { type Notification, type Order, ApiError, api, formatPrice } from "../api";
import { useAuth } from "../auth";
import { useCart } from "../cart";
import { useWishlist } from "../wishlist";
import ProductCard from "../components/ProductCard.vue";
import { type MessageKey, t } from "../locale";

const { state, restore, login, register, logout } = useAuth();
const wishlist = useWishlist();
const cart = useCart();

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
    // the guest cart (if any) was merged server-side — refresh so the badge shows it
    await Promise.all([loadOrders(), loadNotifications(), wishlist.refresh(), cart.refresh()]);
  } catch (e) {
    error.value =
      e instanceof ApiError && e.status === 401
        ? t("account.bad_credentials")
        : e instanceof ApiError && e.status === 422
          ? t("account.check_details")
          : t("common.error_retry");
  } finally {
    busy.value = false;
  }
}

// --- profile self-service (S6) -------------------------------------------------
const profile = ref({ name: "", email: "", phone: "" });
const profileMsg = ref<string | null>(null);
const profileErr = ref<string | null>(null);
const currentPassword = ref("");
const newPassword = ref("");
const passwordMsg = ref<string | null>(null);
const passwordErr = ref<string | null>(null);
const resent = ref(false);

function syncProfileForm() {
  if (!state.customer) return;
  profile.value = {
    name: state.customer.name,
    email: state.customer.email,
    phone: state.customer.phone ?? "",
  };
}

async function saveProfile() {
  profileMsg.value = null;
  profileErr.value = null;
  try {
    state.customer = await api.updateProfile({
      name: profile.value.name,
      email: profile.value.email,
      phone: profile.value.phone,
    });
    syncProfileForm();
    profileMsg.value = state.customer.email_verified
      ? t("account.profile_saved")
      : t("account.profile_saved_verify");
  } catch (e) {
    profileErr.value =
      e instanceof ApiError && e.status === 422
        ? Object.values(e.errors)[0]?.[0] ?? t("account.check_details_short")
        : t("account.profile_error");
  }
}

async function savePassword() {
  passwordMsg.value = null;
  passwordErr.value = null;
  try {
    await api.changePassword(currentPassword.value, newPassword.value);
    currentPassword.value = "";
    newPassword.value = "";
    passwordMsg.value = t("account.password_updated");
  } catch (e) {
    passwordErr.value =
      e instanceof ApiError && e.status === 422
        ? Object.values(e.errors)[0]?.[0] ?? t("account.check_passwords")
        : t("account.password_error");
  }
}

async function resendVerification() {
  await api.resendVerification();
  resent.value = true;
}

async function signOut() {
  await logout();
  orders.value = [];
  notifications.value = [];
}

onMounted(async () => {
  await restore();
  if (state.customer) {
    syncProfileForm();
    await Promise.all([loadOrders(), loadNotifications(), wishlist.refresh()]);
  }
});
</script>

<template>
  <main class="account">
    <p class="eyebrow">{{ t("account.eyebrow") }}</p>

    <!-- signed in -->
    <template v-if="state.customer">
      <div class="account__head">
        <h1>{{ t("account.hello", { name: state.customer.name }) }}</h1>
        <button class="btn" @click="signOut">{{ t("account.sign_out") }}</button>
      </div>
      <p class="account__email">
        {{ state.customer.email }}
        <span v-if="state.customer.email_verified" class="verified">✓ {{ t("account.verified") }}</span>
      </p>

      <p v-if="!state.customer.email_verified" class="verify-note" role="status">
        {{ t("account.not_verified") }}
        <button v-if="!resent" class="linklike" @click="resendVerification">{{ t("account.resend") }}</button>
        <span v-else>{{ t("account.verification_sent") }}</span>
      </p>

      <section class="panel">
        <h2 class="orders__title">{{ t("account.profile") }}</h2>
        <form class="form form--grid" @submit.prevent="saveProfile">
          <label class="field">
            <span>{{ t("account.name") }}</span>
            <input v-model.trim="profile.name" type="text" autocomplete="name" required />
          </label>
          <label class="field">
            <span>{{ t("account.email") }}</span>
            <input v-model.trim="profile.email" type="email" autocomplete="email" required />
          </label>
          <label class="field">
            <span>{{ t("account.phone") }} <em>{{ t("account.phone_hint") }}</em></span>
            <input v-model.trim="profile.phone" type="tel" autocomplete="tel" />
          </label>
          <p v-if="profileErr" class="error" role="alert">{{ profileErr }}</p>
          <p v-if="profileMsg" class="ok" role="status">{{ profileMsg }}</p>
          <button class="btn btn--primary" type="submit">{{ t("account.save_profile") }}</button>
        </form>
      </section>

      <section class="panel">
        <h2 class="orders__title">{{ t("account.change_password") }}</h2>
        <form class="form form--grid" @submit.prevent="savePassword">
          <label class="field">
            <span>{{ t("account.current_password") }}</span>
            <input v-model="currentPassword" type="password" autocomplete="current-password" required />
          </label>
          <label class="field">
            <span>{{ t("account.new_password") }}</span>
            <input v-model="newPassword" type="password" autocomplete="new-password" minlength="8" required />
          </label>
          <p v-if="passwordErr" class="error" role="alert">{{ passwordErr }}</p>
          <p v-if="passwordMsg" class="ok" role="status">{{ passwordMsg }}</p>
          <button class="btn" type="submit">{{ t("account.update_password") }}</button>
        </form>
      </section>

      <section v-if="notifications.length" class="notes">
        <div class="notes__head">
          <h2 class="orders__title">
            {{ t("account.notifications") }}
            <span v-if="unread" class="notes__badge">{{ unread }}</span>
          </h2>
          <button v-if="unread" class="notes__mark" @click="markAllRead">{{ t("account.mark_read") }}</button>
        </div>
        <ul class="notes__list">
          <li v-for="n in notifications" :key="n.id" class="note" :class="{ 'note--unread': !n.read }">
            <span v-if="!n.read" class="note__dot" aria-hidden="true" />
            <span class="note__msg">{{ n.message }}</span>
          </li>
        </ul>
      </section>

      <section v-if="wishlist.state.products.length" class="wish">
        <h2 class="orders__title">{{ t("account.wishlist") }}</h2>
        <div class="wish__grid">
          <ProductCard v-for="p in wishlist.state.products" :key="p.id" :product="p" />
        </div>
      </section>

      <section class="orders">
        <h2 class="orders__title">{{ t("account.orders") }}</h2>
        <p v-if="ordersLoading" class="muted">{{ t("common.loading") }}</p>
        <p v-else-if="orders.length === 0" class="muted">{{ t("account.no_orders") }}</p>
        <ul v-else class="orders__list">
          <li v-for="o in orders" :key="o.id" class="order">
            <RouterLink class="order__link" :to="`/orders/${o.id}`">
              <div>
                <span class="order__id">{{ t("checkout.order") }} #{{ o.id }}</span>
                <span class="order__items">{{ o.items.length }} {{ o.items.length === 1 ? t("account.item_one") : t("account.item_many") }}</span>
              </div>
              <span class="order__status">{{ t(`order.${o.status}` as MessageKey) }}</span>
              <span class="order__total">{{ formatPrice(o.total_cents) }}</span>
            </RouterLink>
          </li>
        </ul>
      </section>
    </template>

    <!-- signed out -->
    <template v-else>
      <h1>{{ mode === "login" ? t("account.sign_in") : t("account.create") }}</h1>
      <p class="account__sub">
        {{ mode === "login" ? t("account.login_sub") : t("account.register_sub") }}
      </p>
      <form class="form" @submit.prevent="submit">
        <label v-if="mode === 'register'" class="field">
          <span>{{ t("account.name") }}</span>
          <input v-model="name" type="text" autocomplete="name" required />
        </label>
        <label class="field">
          <span>{{ t("account.email") }}</span>
          <input v-model="email" type="email" autocomplete="email" required />
        </label>
        <label class="field">
          <span>{{ t("account.password") }}</span>
          <input v-model="password" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" required />
        </label>
        <p v-if="mode === 'login'" class="forgot">
          <RouterLink to="/forgot-password">{{ t("account.forgot") }}</RouterLink>
        </p>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="btn btn--primary submit" :disabled="busy" type="submit">
          {{ busy ? t("common.wait") : mode === "login" ? t("account.sign_in") : t("account.create_btn") }}
        </button>
      </form>
      <p class="switch">
        <template v-if="mode === 'login'">
          {{ t("account.new_here") }} <button class="link" @click="mode = 'register'">{{ t("account.create") }}</button>
        </template>
        <template v-else>
          {{ t("account.have_account") }} <button class="link" @click="mode = 'login'">{{ t("account.sign_in") }}</button>
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
.order__id { font-family: var(--font-display); font-size: var(--text-lg); margin-inline-end: var(--space-3); }
.order__items { color: var(--color-text-muted); font-size: var(--text-sm); }
.order__status { padding: 2px var(--space-3); background: var(--color-accent-soft); color: var(--color-accent); border-radius: var(--radius-full); font-size: var(--text-xs); text-transform: capitalize; }
.order__total { font-weight: var(--weight-medium); min-width: 4rem; text-align: end; }
.muted { color: var(--color-text-muted); }
.verified { color: var(--color-success, #2e7d32); font-size: var(--text-xs); font-weight: 600; margin-inline-start: var(--space-2); }
.verify-note { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-3) var(--space-4); font-size: var(--text-sm); margin: var(--space-4) 0; }
.linklike { background: none; border: none; padding: 0; color: inherit; text-decoration: underline; cursor: pointer; font: inherit; }
.panel { background: var(--color-surface); border-radius: var(--radius-lg); padding: var(--space-6); margin: var(--space-6) 0; }
.form--grid .field { margin-bottom: var(--space-4); }
.form--grid .field em { color: var(--color-text-muted); font-style: normal; font-size: var(--text-xs); }
.ok { color: var(--color-success, #2e7d32); font-size: var(--text-sm); }
.forgot { font-size: var(--text-sm); margin: calc(var(--space-2) * -1) 0 var(--space-3); }
</style>
