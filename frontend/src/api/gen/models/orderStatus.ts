
/**
 * An order's lifecycle state.
 */
export type OrderStatus = typeof OrderStatus[keyof typeof OrderStatus];


export const OrderStatus = {
  pending: 'pending',
  paid: 'paid',
  shipped: 'shipped',
  delivered: 'delivered',
  cancelled: 'cancelled',
  refund_pending: 'refund_pending',
  refunded: 'refunded',
} as const;
