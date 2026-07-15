import type { CouponType } from './couponType';

export interface CouponIn {
  code: string;
  type: CouponType;
  value: number;
  min_subtotal_cents?: number;
  usage_limit?: number | null;
  per_customer_limit?: number | null;
  announce?: boolean;
}
