// The one HTTP seam every generated endpoint goes through (orval mutator): attaches the
// bearer/cart-token headers, raises a typed ApiError with the server's field errors, and
// parses JSON. Per-call headers (e.g. X-Order-Token) ride in the options argument.

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public errors: Record<string, string[]> = {},
  ) {
    super(message);
  }
}

const CART_TOKEN_KEY = "arvel_cart_token";
const AUTH_TOKEN_KEY = "arvel_auth_token";
const LOCALE_KEY = "arvel_locale";

export async function apiFetch<T>(url: string, options: RequestInit): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  const locale = localStorage.getItem(LOCALE_KEY);
  if (locale && !headers.has("Accept-Language")) headers.set("Accept-Language", locale);
  const cart = localStorage.getItem(CART_TOKEN_KEY);
  if (cart && !headers.has("X-Cart-Token")) headers.set("X-Cart-Token", cart);
  const auth = localStorage.getItem(AUTH_TOKEN_KEY);
  if (auth && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${auth}`);
  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    let message = `API ${res.status} for ${options.method ?? "GET"} ${url}`;
    let errors: Record<string, string[]> = {};
    try {
      const body = (await res.json()) as { message?: string; errors?: Record<string, string[]> };
      if (body.message) message = body.message;
      if (body.errors) errors = body.errors;
    } catch {
      // non-JSON error body — keep the generic message
    }
    throw new ApiError(res.status, message, errors);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
