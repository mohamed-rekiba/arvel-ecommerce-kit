#!/usr/bin/env node
// LIVE a11y proof (K1 handoff, Check 2): axe-core driven over the SERVED SPA (built dist,
// preview-served) — not a component snapshot. Boots a real browser, drives the real routes,
// asserts 0 axe violations at impact 'serious'/'critical' per route x theme.
//
// Usage: BASE_URL=http://localhost:4173 node scripts/a11y.mjs
// Requires: the frontend built + served (npm run build && npm run preview -- --port 4173) AND
// the backend API up + seeded (real product/catalog data — see the K1 dev-to-qa notes).

import { chromium } from 'playwright'
import AxeBuilder from '@axe-core/playwright'

const BASE = process.env.BASE_URL ?? 'http://localhost:4173'
const THEMES = ['light', 'dark']
const SERIOUS = new Set(['serious', 'critical'])

async function visit(page, url, theme) {
  await page.goto(url, { waitUntil: 'networkidle' })
  await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), theme)
  // let webfonts finish swapping in and styles settle before scanning — a mid-swap paint can
  // transiently mis-measure text-size/contrast and produce a false-positive violation.
  await page.evaluate(() => document.fonts.ready)
  await page.waitForTimeout(300)
}

async function axe(page, label) {
  const results = await new AxeBuilder({ page }).analyze()
  const bad = results.violations.filter((v) => SERIOUS.has(v.impact ?? ''))
  const summary = results.violations.map((v) => `${v.impact}:${v.id}(${v.nodes.length})`).join(', ')
  console.log(`  ${label}: ${results.violations.length} violation type(s) [${summary || 'none'}]`)
  for (const v of bad) {
    console.log(`    SERIOUS/CRITICAL ${v.id}: ${v.help}`)
    for (const n of v.nodes) console.log(`      - ${n.target.join(' ')}`)
  }
  return bad
}

const API_BASE = process.env.API_BASE_URL ?? 'http://127.0.0.1:8000'

async function firstProductSlug() {
  const res = await fetch(`${API_BASE}/api/products`)
  const json = await res.json()
  return json.data[0].slug
}

async function main() {
  const slug = await firstProductSlug()
  console.log(`using product slug: ${slug}\n`)

  const browser = await chromium.launch()
  let failures = 0
  const report = []

  for (const theme of THEMES) {
    console.log(`\n=== THEME: ${theme} ===`)
    const context = await browser.newContext()
    const page = await context.newPage()

    // home
    await visit(page, `${BASE}/`, theme)
    failures += (await axe(page, `home [${theme}]`)).length

    // catalog — results
    await visit(page, `${BASE}/catalog`, theme)
    failures += (await axe(page, `catalog (results) [${theme}]`)).length

    // catalog — zero results
    await visit(page, `${BASE}/catalog?q=zzzz-no-such-product-zzzz`, theme)
    failures += (await axe(page, `catalog (zero-results) [${theme}]`)).length

    // product detail
    await visit(page, `${BASE}/products/${slug}`, theme)
    failures += (await axe(page, `product [${theme}]`)).length

    // cart — empty
    await visit(page, `${BASE}/cart`, theme)
    failures += (await axe(page, `cart (empty) [${theme}]`)).length

    // add to bag, then cart — populated
    await visit(page, `${BASE}/products/${slug}`, theme)
    const addBtn = page.locator('.pdp__add')
    if (await addBtn.isEnabled().catch(() => false)) {
      await addBtn.click()
      await page.waitForTimeout(300)
    }
    await visit(page, `${BASE}/cart`, theme)
    failures += (await axe(page, `cart (populated) [${theme}]`)).length

    // checkout — form
    await visit(page, `${BASE}/checkout`, theme)
    failures += (await axe(page, `checkout (form) [${theme}]`)).length

    // checkout — submit-error state (blank required fields)
    const placeBtn = page.getByRole('button', { name: /place order|pay|checkout/i }).first()
    if (await placeBtn.count()) {
      await placeBtn.click().catch(() => {})
      await page.waitForTimeout(500)
    }
    failures += (await axe(page, `checkout (submit-error) [${theme}]`)).length

    // admin spot-check (.console register) — pre-auth login screen, no OIDC round-trip needed
    await visit(page, `${BASE}/admin/login`, theme)
    failures += (await axe(page, `admin/login (.console) [${theme}]`)).length

    await context.close()
  }

  await browser.close()

  console.log(
    `\n${failures === 0 ? 'PASS' : 'FAIL'} — ${failures} serious/critical violation(s) total.`
  )
  process.exit(failures === 0 ? 0 : 1)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
