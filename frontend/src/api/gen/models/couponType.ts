
/**
 * How a coupon discounts the order.
 */
export type CouponType = typeof CouponType[keyof typeof CouponType];


export const CouponType = {
  fixed: 'fixed',
  percent: 'percent',
} as const;
