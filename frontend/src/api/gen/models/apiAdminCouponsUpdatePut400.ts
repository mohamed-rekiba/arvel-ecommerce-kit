import type { ApiAdminCouponsUpdatePut400Extra } from './apiAdminCouponsUpdatePut400Extra';

/**
 * Validation Exception
 */
export type ApiAdminCouponsUpdatePut400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminCouponsUpdatePut400Extra;
};
