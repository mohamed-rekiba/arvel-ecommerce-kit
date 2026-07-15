import type { ApiAdminDealsUpdatePatch400Extra } from './apiAdminDealsUpdatePatch400Extra';

/**
 * Validation Exception
 */
export type ApiAdminDealsUpdatePatch400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminDealsUpdatePatch400Extra;
};
