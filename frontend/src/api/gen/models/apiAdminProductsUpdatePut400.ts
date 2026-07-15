import type { ApiAdminProductsUpdatePut400Extra } from './apiAdminProductsUpdatePut400Extra';

/**
 * Validation Exception
 */
export type ApiAdminProductsUpdatePut400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminProductsUpdatePut400Extra;
};
