import type { ApiAdminProductsIndex400Extra } from './apiAdminProductsIndex400Extra';

/**
 * Validation Exception
 */
export type ApiAdminProductsIndex400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminProductsIndex400Extra;
};
