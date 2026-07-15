import type { ApiAdminDealsDestroy400Extra } from './apiAdminDealsDestroy400Extra';

/**
 * Validation Exception
 */
export type ApiAdminDealsDestroy400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminDealsDestroy400Extra;
};
