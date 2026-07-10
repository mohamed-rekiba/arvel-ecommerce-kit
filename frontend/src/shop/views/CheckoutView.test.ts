// The mandated K8 acceptance: a stubbed 422 renders per-field errors + aria-invalid + the
// form-level alert (DESIGN.md §4.5). Stubs only the network seam (api/http::apiFetch) — api,
// ApiError, formatPrice, and the cart store stay real (architecture doc §2).
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CheckoutView from './CheckoutView.vue'
import { makeCart, makeCartLine, makeShippingMethod } from '../../test/fixtures'

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

describe('CheckoutView', () => {
  it('renders cart line items and the subtotal', async () => {
    const cart = makeCart({
      items: [makeCartLine({ product_name: 'Canvas Tote', line_total_cents: 4500 })],
      total_cents: 4500
    })
    mockRoutes({
      'GET /api/cart': () => cart,
      'GET /api/shipping-methods': () => []
    })

    const wrapper = mount(CheckoutView)
    await flushPromises()

    expect(wrapper.text()).toContain('Canvas Tote')
    expect(wrapper.text()).toContain('$45.00')
  })

  it('shows the empty-cart state when the cart has no items', async () => {
    mockRoutes({
      'GET /api/cart': () => makeCart({ items: [], total_cents: 0 }),
      'GET /api/shipping-methods': () => []
    })

    const wrapper = mount(CheckoutView)
    await flushPromises()

    expect(wrapper.text()).toContain('Your cart is empty.')
    expect(wrapper.find('form').exists()).toBe(false)
  })

  it('renders per-field 422 errors with role=alert + aria-invalid, and the form-level alert', async () => {
    const cart = makeCart({ items: [makeCartLine()] })
    mockRoutes({
      'GET /api/cart': () => cart,
      'GET /api/shipping-methods': () => [makeShippingMethod()],
      'POST /api/checkout': () => {
        throw new ApiError(422, 'The given data was invalid.', {
          email: ['The email field is required.'],
          line1: ['The line1 field is required.'],
          city: ['The city field is required.']
        })
      }
    })

    const wrapper = mount(CheckoutView)
    await flushPromises()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    // form-level alert
    const formError = wrapper.find('p.error[role="alert"]')
    expect(formError.exists()).toBe(true)
    expect(formError.text()).toBe('Please check the highlighted fields.')

    // per-field alerts + aria-invalid, one per errored field
    const expectations: Array<[autocomplete: string, message: string]> = [
      ['email', 'The email field is required.'],
      ['address-line1', 'The line1 field is required.'],
      ['address-level2', 'The city field is required.']
    ]
    for (const [autocomplete, message] of expectations) {
      const input = wrapper.get(`[autocomplete="${autocomplete}"]`)
      expect(input.attributes('aria-invalid')).toBe('true')
      const label = input.element.closest('label')
      expect(label).not.toBeNull()
      const fieldError = label!.querySelector('small.field-error')
      expect(fieldError).not.toBeNull()
      expect(fieldError!.getAttribute('role')).toBe('alert')
      expect(fieldError!.textContent).toBe(message)
    }
  })
})
