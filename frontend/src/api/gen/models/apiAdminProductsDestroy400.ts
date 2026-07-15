import type { ApiAdminProductsDestroy400Extra } from './apiAdminProductsDestroy400Extra';

/**
 * Validation Exception
 */
export type ApiAdminProductsDestroy400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminProductsDestroy400Extra;
};
