
/**
 * A refund's state, mirrored from the gateway (K15) — the reverse of PaymentStatus.
 */
export type RefundStatus = typeof RefundStatus[keyof typeof RefundStatus];


export const RefundStatus = {
  pending: 'pending',
  succeeded: 'succeeded',
  failed: 'failed',
} as const;
