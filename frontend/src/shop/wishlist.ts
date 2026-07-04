// Reactive singleton — saved server-side per customer; requires a signed-in bearer session.
import { reactive } from "vue";
import { type Product, api, authToken } from "./api";

const state = reactive<{ ids: Set<number>; products: Product[]; ready: boolean }>({
  ids: new Set<number>(),
  products: [],
  ready: false,
});

export function useWishlist() {
  async function refresh() {
    if (!authToken.get()) {
      state.ids = new Set();
      state.products = [];
      state.ready = true;
      return;
    }
    try {
      const list = await api.wishlist();
      state.products = list;
      state.ids = new Set(list.map((p) => p.id));
    } catch {
      /* not authorized — leave empty */
    }
    state.ready = true;
  }

  async function toggle(productId: number): Promise<boolean> {
    const res = await api.toggleWishlist(productId);
    if (res.saved) state.ids.add(productId);
    else state.ids.delete(productId);
    await refresh();
    return res.saved;
  }

  const has = (id: number) => state.ids.has(id);
  return { state, refresh, toggle, has };
}
