// Admin auth store. Bearer session (email/password → personal-access token) for the RBAC back-office
// users. Which admin nav/actions are permitted is enforced server-side by the RBAC Gate (403/404); the
// SPA just reflects failures. (Keycloak-OIDC is the production login; it resolves the same admin User
// via the /admin OIDC path and would issue an equivalent bearer session.)
import { reactive } from "vue";
import { type User, api, token } from "./api";

const state = reactive<{ user: User | null; ready: boolean }>({ user: null, ready: false });

export function useAuth() {
  async function restore() {
    if (token.get()) {
      try {
        state.user = await api.me();
      } catch {
        token.clear();
        state.user = null;
      }
    }
    state.ready = true;
  }
  async function login(email: string, password: string) {
    await api.login(email, password);
    state.user = await api.me();
  }
  function logout() {
    token.clear();
    state.user = null;
  }
  return { state, restore, login, logout };
}
