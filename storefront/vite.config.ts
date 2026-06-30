import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// The storefront is a decoupled SPA; in dev it proxies /api to the arvel server (arvel serve → :8000).
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
