import type { ApiAdminOrdersRefund400Extra } from './apiAdminOrdersRefund400Extra';

/**
 * Validation Exception
 */
export type ApiAdminOrdersRefund400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminOrdersRefund400Extra;
};
