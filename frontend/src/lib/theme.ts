// Light/dark theme — persisted, defaults to the OS preference. The no-flash initial set happens in
// index.html (pre-paint); this module is the reactive toggle the UI binds to.
import { ref } from "vue";

export type Theme = "light" | "dark";
const KEY = "arvel_theme";

function preferred(): Theme {
  const saved = localStorage.getItem(KEY) as Theme | null;
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export const theme = ref<Theme>(preferred());

function apply(t: Theme) {
  document.documentElement.setAttribute("data-theme", t);
}

export function initTheme() {
  apply(theme.value);
}

export function toggleTheme() {
  theme.value = theme.value === "dark" ? "light" : "dark";
  localStorage.setItem(KEY, theme.value);
  apply(theme.value);
}
