import type { ApiAdminCouponsUpdatePatch400Extra } from './apiAdminCouponsUpdatePatch400Extra';

/**
 * Validation Exception
 */
export type ApiAdminCouponsUpdatePatch400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminCouponsUpdatePatch400Extra;
};
