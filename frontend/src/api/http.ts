// The orval mutator — every generated endpoint funnels through here for auth headers + error shaping.
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public errors: Record<string, string[]> = {}
  ) {
    super(message)
  }
}

const CART_TOKEN_KEY = 'arvel_cart_token'
const AUTH_TOKEN_KEY = 'arvel_auth_token'
const LOCALE_KEY = 'arvel_locale'

export async function apiFetch<T>(url: string, options: RequestInit): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  const locale = localStorage.getItem(LOCALE_KEY)
  if (locale && !headers.has('Accept-Language')) headers.set('Accept-Language', locale)
  const cart = localStorage.getItem(CART_TOKEN_KEY)
  if (cart && !headers.has('X-Cart-Token')) headers.set('X-Cart-Token', cart)
  const auth = localStorage.getItem(AUTH_TOKEN_KEY)
  if (auth && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${auth}`)
  // JSON bodies are pre-stringified; FormData/Blob set their own content type (boundary included)
  if (typeof options.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(url, { ...options, headers })
  if (res.status === 503) {
    // maintenance mode (arvel down) — let the shell swap in the designed screen
    window.dispatchEvent(new CustomEvent('arvel:maintenance'))
  }
  if (!res.ok) {
    let message = `API ${res.status} for ${options.method ?? 'GET'} ${url}`
    let errors: Record<string, string[]> = {}
    try {
      const body = (await res.json()) as {
        message?: string
        errors?: Record<string, string[]>
      }
      if (body.message) message = body.message
      if (body.errors) errors = body.errors
    } catch {
      // non-JSON error body — keep the generic message
    }
    throw new ApiError(res.status, message, errors)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}
