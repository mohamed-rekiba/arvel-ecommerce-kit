import { createApp } from "vue";
import PrimeVue from "primevue/config";
import "primeicons/primeicons.css";
import "./styles/tokens.css";
import "./styles/base.css";
import { initTheme } from "./lib/theme";
import { ArvelPreset } from "./lib/primevue-preset";
import App from "./App.vue";
import router from "./router";

initTheme();
createApp(App)
  .use(router)
  .use(PrimeVue, {
    theme: { preset: ArvelPreset, options: { darkModeSelector: '[data-theme="dark"]' } },
  })
  .mount("#app");
