import type { AddressOut } from './addressOut';
import type { AdminOrderCustomerOut } from './adminOrderCustomerOut';
import type { AdminOrderEventOut } from './adminOrderEventOut';
import type { AdminOrderPaymentOut } from './adminOrderPaymentOut';
import type { AdminOrderRefundOut } from './adminOrderRefundOut';
import type { Currency } from './currency';
import type { OrderLineOut } from './orderLineOut';
import type { OrderStatus } from './orderStatus';
import type { PaymentMethod } from './paymentMethod';

export interface AdminOrderDetailOut {
  id: number;
  status: OrderStatus;
  contact_email: string;
  address: AddressOut;
  subtotal_cents: number;
  shipping_cents: number;
  tax_cents: number;
  coupon_code: string | null;
  discount_cents: number;
  total_cents: number;
  currency: Currency;
  payment_method: PaymentMethod;
  shipping_method: string;
  tracking_number: string | null;
  customer: AdminOrderCustomerOut | null;
  items: OrderLineOut[];
  payments: AdminOrderPaymentOut[];
  refunds: AdminOrderRefundOut[];
  history: AdminOrderEventOut[];
}
