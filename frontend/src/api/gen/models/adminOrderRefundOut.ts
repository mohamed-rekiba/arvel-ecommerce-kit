import type { RefundStatus } from './refundStatus';

export interface AdminOrderRefundOut {
  id: number;
  gateway_charge_id: string;
  gateway_refund_id: string | null;
  amount_cents: number;
  status: RefundStatus;
  restock: boolean;
  created_at: string | null;
}
