import type { PaymentStatus } from './paymentStatus';

export interface AdminOrderPaymentOut {
  id: number;
  charge_id: string;
  amount_cents: number;
  status: PaymentStatus;
  created_at: string | null;
}
