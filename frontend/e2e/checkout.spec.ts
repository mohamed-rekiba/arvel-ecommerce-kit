// LIVE checkout e2e (K8's mandated acceptance): drives a real browser through the served SPA +
// a debug backend (dev gateway registered) + a running queue worker (`make e2e` owns that boot;
// see scripts/a11y.mjs for the sibling live-boot pattern). No network mock on this path — the
// same code path a real buyer walks.
import { expect, test } from 'playwright/test'

test('browse, add to cart, check out, and pay reaches placed then paid', async ({ page }) => {
  test.setTimeout(60_000)

  await page.goto('/')
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

  await page.locator('input[autocomplete="email"]').fill('buyer@example.com')
  await page.locator('input[autocomplete="name"]').fill('Jane Buyer')
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

  // pay → the dev gateway queues DeliverGatewayWebhook → the worker delivers charge.succeeded →
  // the order flips paid → the SPA's own poll (20×1s) picks it up. This assertion's timeout is
  // raised above that 20s poll ceiling so a live-but-slightly-slow webhook isn't a false negative.
  await page.locator('.pay button.act--primary').click()
  await expect(page.locator('.pay__done')).toBeVisible({ timeout: 25_000 })
})
