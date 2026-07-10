// LIVE checkout e2e (K8's mandated acceptance, K9-extended): drives a real browser through the
// served SPA + a debug backend (dev gateway registered) + a running queue worker (`make e2e` owns
// that boot; see scripts/a11y.mjs for the sibling live-boot pattern). No network mock on this
// path — the same code path a real buyer walks.
//
// K9: the order's private channel is user-scoped, so this now signs in first, then asserts the
// paid confirmation arrives via the pushed `OrderPaid` websocket event — not a poll. The
// `setInterval` poll loop is gone from CheckoutView; this test's zero-poll assertion is the
// non-vacuous proof of that (restoring the poll would make it fail).
import { expect, test } from 'playwright/test'

test('sign in, check out, and pay reaches paid via the pushed OrderPaid event — zero order polling', async ({
  page
}) => {
  test.setTimeout(60_000)
  const email = `buyer+${Date.now()}@example.com`
  const pw = `e2e-${Date.now()}` // throwaway, generated per run — not a real credential

  // sign in first — the private order channel (K9) is user-scoped
  await page.goto('/account')
  await page.getByRole('button', { name: 'Create an account' }).click()
  await page.locator('input[autocomplete="name"]').fill('Jane Buyer')
  await page.locator('input[autocomplete="email"]').fill(email)
  await page.locator('input[autocomplete="new-password"]').fill(pw)
  const [registered] = await Promise.all([
    page.waitForResponse((res) => res.url().includes('/api/register')),
    page.getByRole('button', { name: 'Create account' }).click()
  ])
  expect(registered.status()).toBe(201)

  await page.goto('/catalog')

  // skip a sold-out card (.media__out is the ProductCard's own out-of-stock badge) so the PDP
  // lands on a product with an addable, in-stock variant.
  const card = page
    .locator('.card')
    .filter({ hasNot: page.locator('.media__out') })
    .first()
  await expect(card).toBeVisible()
  await card.locator('.name').click()
  await expect(page).toHaveURL(/\/products\//)

  const addButton = page.locator('.pdp__add')
  await expect(addButton).toBeEnabled()
  await addButton.click()
  await expect(addButton).toBeEnabled() // round-trips through /api/cart/items before we navigate on

  await page.goto('/checkout')

  await page.locator('input[autocomplete="address-line1"]').fill('1 Market St')
  await page.locator('input[autocomplete="address-level2"]').fill('Springfield')
  await page.locator('input[autocomplete="postal-code"]').fill('11111')

  // shipping method (K16) — pick whichever rate the server offered
  const shippingRadio = page.locator('input[name="sm"]').first()
  if (await shippingRadio.count()) await shippingRadio.check()

  // payment method — gateway, so the dev-gateway/webhook loop below actually runs
  await page.locator('input[name="pm"][value="gateway"]').check()

  await page.getByRole('button', { name: 'Place order' }).click()

  // placed: confirmation heading + order id
  await expect(page.locator('h1')).toHaveText('Order placed')
  await expect(page.locator('.confirm__line strong')).toHaveText(/^#\d+$/)
  const orderId = (await page.locator('.confirm__line strong').innerText()).replace('#', '')

  // K9: no GET /api/orders/{id} polling once pay starts — the confirmation advances via the
  // socket push, not a poll loop. Counting from here (not from page load) so the one-time initial
  // order fetch that renders the confirmation doesn't false-positive this assertion.
  let pollCount = 0
  const orderEndpoint = new RegExp(`/api/orders/${orderId}(?:\\?|$)`)
  page.on('request', (req) => {
    if (req.method() === 'GET' && orderEndpoint.test(req.url())) pollCount += 1
  })

  await page.locator('.pay button.act--primary').click()
  await expect(page.locator('.pay__done')).toBeVisible({ timeout: 25_000 })
  expect(pollCount).toBe(0)
})
