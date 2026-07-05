// RBAC is enforced server-side (403/404 on the Gate) — this store just reflects failures, it doesn't gate nav.
import { reactive } from 'vue'
import { type User, api, token } from './api'

const state = reactive<{ user: User | null; ready: boolean }>({
  user: null,
  ready: false
})

export function useAuth() {
  async function restore() {
    if (token.get()) {
      try {
        state.user = await api.me()
      } catch {
        token.clear()
        state.user = null
      }
    }
    state.ready = true
  }
  async function login(email: string, password: string) {
    await api.login(email, password)
    state.user = await api.me()
  }
  function logout() {
    token.clear()
    state.user = null
  }
  return { state, restore, login, logout }
}
