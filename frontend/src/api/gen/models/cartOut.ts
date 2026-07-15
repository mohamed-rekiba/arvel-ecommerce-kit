import type { CartLineOut } from './cartLineOut';

export interface CartOut {
  id: number | null;
  items: CartLineOut[];
  total_cents: number;
  coupon_code: string | null;
  discount_cents: number;
  cart_token?: string | null;
}
