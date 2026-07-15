import type { ApiAdminOrdersStatus400Extra } from './apiAdminOrdersStatus400Extra';

/**
 * Validation Exception
 */
export type ApiAdminOrdersStatus400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminOrdersStatus400Extra;
};
