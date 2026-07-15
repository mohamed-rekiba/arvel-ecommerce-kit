
export interface CouponUpdateIn {
  active?: boolean | null;
  usage_limit?: number | null;
  per_customer_limit?: number | null;
  min_subtotal_cents?: number | null;
  announce?: boolean | null;
}
