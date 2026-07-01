import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// The admin SPA — a decoupled Vue app (separate from the storefront); in dev it proxies /api to the
// arvel server (arvel serve → :8000). Entry: http://localhost:5174
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
