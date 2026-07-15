
/**
 * A payment's state, mirrored from the gateway.
 */
export type PaymentStatus = typeof PaymentStatus[keyof typeof PaymentStatus];


export const PaymentStatus = {
  pending: 'pending',
  succeeded: 'succeeded',
  failed: 'failed',
} as const;
