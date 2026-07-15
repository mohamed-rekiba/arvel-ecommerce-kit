import type { ApiAdminProductsRestore400Extra } from './apiAdminProductsRestore400Extra';

/**
 * Validation Exception
 */
export type ApiAdminProductsRestore400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminProductsRestore400Extra;
};
