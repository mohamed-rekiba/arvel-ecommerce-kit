// A tiny shared cart store (reactive singleton) — the header badge and the cart/checkout views all
// read the same state. The guest cart token is handled inside api.ts (localStorage + X-Cart-Token).
import { computed, reactive } from "vue";
import { type Cart, api } from "./api";

const state = reactive<{ cart: Cart | null; loading: boolean }>({ cart: null, loading: false });

const count = computed(() =>
  (state.cart?.items ?? []).reduce((n, line) => n + line.quantity, 0),
);

export function useCart() {
  async function refresh() {
    state.loading = true;
    try {
      state.cart = await api.cart();
    } finally {
      state.loading = false;
    }
  }
  async function add(variantId: number, qty = 1) {
    state.cart = await api.addToCart(variantId, qty);
  }
  async function update(id: number, qty: number) {
    state.cart = await api.updateCartItem(id, qty);
  }
  async function remove(id: number) {
    state.cart = await api.removeCartItem(id);
  }
  async function checkout() {
    const order = await api.checkout();
    state.cart = null;
    return order;
  }
  return { state, count, refresh, add, update, remove, checkout };
}
