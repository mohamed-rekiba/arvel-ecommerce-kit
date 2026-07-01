import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// One consolidated SPA (storefront + admin). In dev it proxies /api to the arvel server (arvel serve →
// :8000). The admin section is split into its own chunk so a storefront visitor never downloads it.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("/src/admin/")) return "admin";
          return undefined;
        },
      },
    },
  },
});
