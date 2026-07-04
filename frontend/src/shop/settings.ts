// Server defaults mean values are always present; the fallbacks here only cover a failed fetch.
import { reactive } from "vue";
import { api } from "./api";

const state = reactive<{ values: Record<string, string>; ready: boolean }>({
  values: {},
  ready: false,
});

let loading: Promise<void> | null = null;

export function useSettings() {
  function load(): Promise<void> {
    loading ??= api
      .publicSettings()
      .then((res) => {
        state.values = res.values;
      })
      .catch(() => {})
      .then(() => {
        state.ready = true;
      });
    return loading;
  }

  const get = (key: string, fallback = "") => state.values[key] || fallback;

  return { state, load, get };
}
