import type { ApiAdminProductsUpdatePatch400Extra } from './apiAdminProductsUpdatePatch400Extra';

/**
 * Validation Exception
 */
export type ApiAdminProductsUpdatePatch400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminProductsUpdatePatch400Extra;
};
