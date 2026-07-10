import { defineConfig, devices } from 'playwright/test'

// LIVE checkout e2e (K8) — mirrors scripts/a11y.mjs's boot: the SPA built + preview-served,
// backend up+seeded+debug (dev gateway registered) + a queue worker running (Makefile `e2e`
// target owns backend/infra/worker; this config owns the SPA's own preview server).
const BASE_URL = process.env.BASE_URL ?? 'http://localhost:4173'

export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure'
  },
  webServer: {
    command: 'npm run preview -- --port 4173',
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }]
})
