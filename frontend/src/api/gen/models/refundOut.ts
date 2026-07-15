import type { RefundStatus } from './refundStatus';

export interface RefundOut {
  amount_cents: number;
  status: RefundStatus;
  created_at: string | null;
}
