import type { ApiOrdersInvoice400Extra } from './apiOrdersInvoice400Extra';

/**
 * Validation Exception
 */
export type ApiOrdersInvoice400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiOrdersInvoice400Extra;
};
