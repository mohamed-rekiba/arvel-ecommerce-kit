import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CartView from './CartView.vue'
import { makeCart, makeCartLine } from '../../test/fixtures'

vi.mock('../../api/http', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/http')>()
  return { ...actual, apiFetch: vi.fn() }
})
import { ApiError, apiFetch } from '../../api/http'

const fetchMock = vi.mocked(apiFetch)

function mockRoutes(handlers: Record<string, () => unknown>) {
  fetchMock.mockImplementation(async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? 'GET'} ${url}`
    const handler = handlers[key]
    if (!handler) throw new Error(`unhandled mock request: ${key}`)
    return handler()
  })
}

beforeEach(() => {
  fetchMock.mockReset()
  localStorage.clear()
})

describe('CartView', () => {
  it('renders per-line totals and the cart total (total minus discount)', async () => {
    const cart = makeCart({
      items: [
        makeCartLine({ id: 1, product_name: 'Canvas Tote', line_total_cents: 4500 }),
        makeCartLine({ id: 2, product_name: 'Wool Scarf', line_total_cents: 3000 })
      ],
      total_cents: 7500,
      coupon_code: 'SAVE10',
      discount_cents: 750
    })
    mockRoutes({ 'GET /api/cart': () => cart })

    const wrapper = mount(CartView)
    await flushPromises()

    expect(wrapper.text()).toContain('Canvas Tote')
    expect(wrapper.text()).toContain('Wool Scarf')
    expect(wrapper.text()).toContain('$45.00')
    expect(wrapper.text()).toContain('$30.00')
    // cart total is total_cents - discount_cents = 7500 - 750 = 6750
    expect(wrapper.find('.summary__row--total').text()).toContain('$67.50')
  })

  it('shows the empty state when the cart has no items', async () => {
    mockRoutes({ 'GET /api/cart': () => makeCart({ items: [], total_cents: 0 }) })

    const wrapper = mount(CartView)
    await flushPromises()

    expect(wrapper.text()).toContain('Your cart is empty.')
    expect(wrapper.find('.line').exists()).toBe(false)
  })

  it('renders a coupon-apply failure as .coupon__error[role="alert"]', async () => {
    const cart = makeCart({ items: [makeCartLine()], coupon_code: null })
    mockRoutes({
      'GET /api/cart': () => cart,
      'POST /api/cart/coupon': () => {
        throw new ApiError(422, 'Validation failed.', { code: ['Invalid coupon code.'] })
      }
    })

    const wrapper = mount(CartView)
    await flushPromises()

    await wrapper.get('.coupon input').setValue('BADCODE')
    await wrapper.get('form.coupon').trigger('submit')
    await flushPromises()

    const error = wrapper.find('.coupon__error')
    expect(error.exists()).toBe(true)
    expect(error.attributes('role')).toBe('alert')
    expect(error.text()).toBe('Invalid coupon code.')
  })
})
