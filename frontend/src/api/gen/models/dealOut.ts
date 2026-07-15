import type { ProductOut } from './productOut';

export interface DealOut {
  id: number;
  percent_off: number;
  deal_price_cents: number;
  ends_at: string;
  available: number;
  sold: number;
  product: ProductOut;
}
