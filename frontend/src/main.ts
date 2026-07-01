import { createApp } from "vue";
import "./styles/tokens.css";
import "./styles/base.css";
import { initTheme } from "./lib/theme";
import App from "./App.vue";
import router from "./router";

initTheme();
createApp(App).use(router).mount("#app");
