import type { AddressIn } from './addressIn';
import type { PaymentMethod } from './paymentMethod';

/**
 * Checkout submission: contact email (required for guests; defaults to the account email for
 * signed-in customers) + shipping address — inline, or a saved address-book id (owned), plus
 * the payment method (gateway = pay after placing; cod = collect on delivery) and the shipping
 * method CODE (the rate is resolved server-side from it — never sent by the client, DR-0064).
 */
export interface CheckoutIn {
  email?: string | null;
  address?: null | AddressIn;
  address_id?: number | null;
  payment_method?: PaymentMethod;
  shipping_method?: string;
}
