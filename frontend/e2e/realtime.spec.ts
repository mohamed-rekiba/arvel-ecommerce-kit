// K9 live proof (companion to checkout.spec.ts's push-not-poll assertion): a dropped/blocked
// relay socket falls back gracefully (no dead end, no unhandled error), and the private order
// channel's channel-auth denies a non-owner while authorizing the owner — both against the real
// served app + a running queue worker (`make e2e` owns that boot).
import { expect, test } from 'playwright/test'

test('a dropped/blocked socket falls back to one reconciliation fetch — no dead end, no unhandled error', async ({
  page
}) => {
  test.setTimeout(30_000)
  const pageErrors: Error[] = []
  page.on('pageerror', (err) => pageErrors.push(err))

  // every /ws connection attempt is accepted then immediately closed — simulates a blocked/
  // dropped relay socket without touching the server.
  await page.routeWebSocket(/\/ws$/, (ws) => {
    ws.close()
  })

  const email = `buyer+${Date.now()}@example.com`
  const pw = `e2e-${Date.now()}` // throwaway, generated per run — not a real credential
  await page.goto('/account')
  await page.getByRole('button', { name: 'Create an account' }).click()
  await page.locator('input[autocomplete="name"]').fill('Jane Buyer')
  await page.locator('input[autocomplete="email"]').fill(email)
  await page.locator('input[autocomplete="new-password"]').fill(pw)
  await Promise.all([
    page.waitForResponse((res) => res.url().includes('/api/register')),
    page.getByRole('button', { name: 'Create account' }).click()
  ])

  await page.goto('/catalog')
  const card = page
    .locator('.card')
    .filter({ hasNot: page.locator('.media__out') })
    .first()
  await card.locator('.name').click()
  await page.locator('.pdp__add').click()

  await page.goto('/checkout')
  await page.locator('input[autocomplete="address-line1"]').fill('1 Market St')
  await page.locator('input[autocomplete="address-level2"]').fill('Springfield')
  await page.locator('input[autocomplete="postal-code"]').fill('11111')
  const shippingRadio = page.locator('input[name="sm"]').first()
  if (await shippingRadio.count()) await shippingRadio.check()
  await page.locator('input[name="pm"][value="gateway"]').check()
  await page.getByRole('button', { name: 'Place order' }).click()
  await expect(page.locator('h1')).toHaveText('Order placed')

  let reconciliationFetches = 0
  page.on('request', (req) => {
    if (req.method() === 'GET' && /\/api\/orders\/\d+/.test(req.url())) reconciliationFetches += 1
  })

  await page.locator('.pay button.act--primary').click()
  // settles neutral — no dead end (the deleted `pay_slow` copy never appears), and no more than
  // the ONE reconciliation fetch the graceful fallback makes.
  await expect(page.getByText(/taking longer than expected/i)).toHaveCount(0)
  await page.waitForTimeout(1500) // give the single fallback fetch a moment to land
  expect(reconciliationFetches).toBe(1)
  expect(pageErrors).toEqual([])
})

test('the private order channel denies a non-owner and authorizes the owner', async ({
  request
}) => {
  const pw = `e2e-${Date.now()}` // throwaway, generated per run — not a real credential
  const owner = await request
    .post('/api/register', {
      data: { name: 'Owner', email: `owner+${Date.now()}@example.com`, password: pw }
    })
    .then((r) => r.json())
  const intruder = await request
    .post('/api/register', {
      data: { name: 'Intruder', email: `intruder+${Date.now()}@example.com`, password: pw }
    })
    .then((r) => r.json())

  const products = await request.get('/api/products').then((r) => r.json())
  const variantId = products.data[0].variants[0].id
  await request.post('/api/cart/items', {
    headers: { Authorization: `Bearer ${owner.token}` },
    data: { product_variant_id: variantId, quantity: 1 }
  })
  const order = await request
    .post('/api/checkout', {
      headers: { Authorization: `Bearer ${owner.token}` },
      data: {
        address: {
          name: 'Owner',
          line1: '1 Market St',
          line2: null,
          city: 'Springfield',
          postal_code: '11111',
          country: 'US'
        }
      }
    })
    .then((r) => r.json())

  const channel = `private-order.${order.id}`
  const denied = await request.post('/broadcasting/auth', {
    headers: { Authorization: `Bearer ${intruder.token}` },
    form: { socket_id: 'e2e-socket', channel_name: channel }
  })
  expect(denied.status()).toBe(403)

  const allowed = await request.post('/broadcasting/auth', {
    headers: { Authorization: `Bearer ${owner.token}` },
    form: { socket_id: 'e2e-socket', channel_name: channel }
  })
  expect(allowed.status()).toBe(200)
  expect((await allowed.json()).auth).toBeTruthy()
})
