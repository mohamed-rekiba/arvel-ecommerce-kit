import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

// Node 22+'s experimental global `localStorage` is installed before happy-dom gets a chance to
// provide its own, and without --localstorage-file it's a dead stub — every component that reads
// localStorage on import (src/lib/i18n.ts) then throws. Disabling it here, only under vitest
// (before it forks worker processes, which inherit process.env), restores happy-dom's real
// Storage impl without touching the flags `vite dev`/`vite build` run with.
if (process.env.VITEST) {
  process.env.NODE_OPTIONS = `${process.env.NODE_OPTIONS ?? ''} --no-experimental-webstorage`.trim()
}

// One consolidated SPA (storefront + admin). In dev it proxies /api to the arvel server (arvel serve →
// :8000). The admin views are already lazy-loaded (router uses `() => import()`), so a storefront
// visitor never downloads them — and each admin route splits into its own chunk, so opening the admin
// login page doesn't pull in the whole (DataTable-heavy) admin bundle. Don't add a manualChunks rule
// that collapses all of /src/admin/ back into one chunk; it defeats that per-route splitting.
// K9: /broadcasting (arvel's channel-auth endpoint) and /ws (the BroadcastRelay) live outside
// /api at the server's ASGI root, so they need their own proxy entries — /ws with `ws: true` for
// the websocket upgrade. `vite preview` (the e2e harness) reuses this same `server.proxy` config.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/broadcasting': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'http://localhost:8000', changeOrigin: true, ws: true }
    }
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['src/test/setup.ts'],
    include: ['src/**/*.test.ts'],
    exclude: ['e2e/**']
  }
})
