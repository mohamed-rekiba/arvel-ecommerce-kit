
export interface PaymentOut {
  payment_id: number;
  charge_id: string;
  client_secret: string | null;
  status: string;
}
