import type { CouponType } from './couponType';

export interface AdminCouponOut {
  id: number;
  code: string;
  type: CouponType;
  value: number;
  min_subtotal_cents: number;
  usage_limit: number | null;
  per_customer_limit: number | null;
  uses: number;
  active: boolean;
  announce: boolean;
  starts_at: string | null;
  ends_at: string | null;
}
