import type { ApiAdminDealsUpdatePut400Extra } from './apiAdminDealsUpdatePut400Extra';

/**
 * Validation Exception
 */
export type ApiAdminDealsUpdatePut400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminDealsUpdatePut400Extra;
};
