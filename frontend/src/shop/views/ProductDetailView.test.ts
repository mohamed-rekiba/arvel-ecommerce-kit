import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ProductDetailView from './ProductDetailView.vue'
import { router } from '../../test/setup'
import { makeCart, makeProduct, makeVariant } from '../../test/fixtures'

vi.mock('../../api/http', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/http')>()
  return { ...actual, apiFetch: vi.fn() }
})
import { apiFetch } from '../../api/http'

const fetchMock = vi.mocked(apiFetch)

function mockRoutes(handlers: Record<string, (init: RequestInit) => unknown>) {
  fetchMock.mockImplementation(async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? 'GET'} ${url}`
    const handler = handlers[key]
    if (!handler) throw new Error(`unhandled mock request: ${key}`)
    return handler(init)
  })
}

beforeEach(() => {
  fetchMock.mockReset()
  localStorage.clear()
})

describe('ProductDetailView', () => {
  it('adds to cart with the selected variant and quantity', async () => {
    await router.push('/products/canvas-tote')
    await router.isReady()

    const variant = makeVariant({ id: 7, stock: 10 })
    const product = makeProduct({ slug: 'canvas-tote', variants: [variant] })
    mockRoutes({
      'GET /api/products/canvas-tote': () => product,
      'POST /api/cart/items': (init) => {
        const body = JSON.parse(init.body as string) as {
          product_variant_id: number
          quantity: number
        }
        expect(body).toEqual({ product_variant_id: 7, quantity: 2 })
        return makeCart()
      }
    })

    const wrapper = mount(ProductDetailView)
    await flushPromises()

    await wrapper.get('button[aria-label="increase"]').trigger('click')
    await wrapper.get('.pdp__add').trigger('click')
    await flushPromises()

    const addCalls = fetchMock.mock.calls.filter(([url]) => url === '/api/cart/items')
    expect(addCalls).toHaveLength(1)
  })

  it('disables add-to-cart and shows notify-me for an out-of-stock variant', async () => {
    await router.push('/products/sold-out-mug')
    await router.isReady()

    const variant = makeVariant({ id: 9, stock: 0 })
    const product = makeProduct({ slug: 'sold-out-mug', variants: [variant] })
    mockRoutes({
      'GET /api/products/sold-out-mug': () => product
    })

    const wrapper = mount(ProductDetailView)
    await flushPromises()

    const addButton = wrapper.get('.pdp__add')
    expect(addButton.attributes('disabled')).toBeDefined()
    expect(wrapper.find('.pdp__alert-btn').exists()).toBe(true)
  })
})
