// Guest checkout still works via the cart token; signing in additionally unlocks order history.
import { reactive } from "vue";
import { type Customer, api, authToken } from "./api";

const state = reactive<{ customer: Customer | null; ready: boolean }>({ customer: null, ready: false });

export function useAuth() {
  async function restore() {
    if (authToken.get()) {
      try {
        state.customer = await api.me();
      } catch {
        authToken.clear();
      }
    }
    state.ready = true;
  }
  async function login(email: string, password: string) {
    await api.login(email, password);
    state.customer = await api.me();
  }
  async function register(name: string, email: string, password: string) {
    await api.register(name, email, password);
    state.customer = await api.me();
  }
  async function logout() {
    await api.logout();
    state.customer = null;
  }
  return { state, restore, login, register, logout };
}
