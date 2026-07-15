
/**
 * How the order is settled: the payment gateway after placing, or cash on delivery.
 */
export type PaymentMethod = typeof PaymentMethod[keyof typeof PaymentMethod];


export const PaymentMethod = {
  cod: 'cod',
  gateway: 'gateway',
} as const;
