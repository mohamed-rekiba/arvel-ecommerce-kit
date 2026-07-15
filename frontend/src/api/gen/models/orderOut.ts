import type { AddressOut } from './addressOut';
import type { Currency } from './currency';
import type { OrderLineOut } from './orderLineOut';
import type { OrderStatus } from './orderStatus';
import type { OrderTimelineOut } from './orderTimelineOut';
import type { PaymentMethod } from './paymentMethod';
import type { PaymentStatus } from './paymentStatus';
import type { RefundOut } from './refundOut';

export interface OrderOut {
  id: number;
  status: OrderStatus;
  token: string;
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
  payment_status: PaymentStatus | null;
  shipping_method: string;
  tracking_number: string | null;
  items: OrderLineOut[];
  placed_at?: string | null;
  timeline?: OrderTimelineOut[] | null;
  refund?: RefundOut | null;
}
