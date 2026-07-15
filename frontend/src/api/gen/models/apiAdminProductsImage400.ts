import type { ApiAdminProductsImage400Extra } from './apiAdminProductsImage400Extra';

/**
 * Validation Exception
 */
export type ApiAdminProductsImage400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminProductsImage400Extra;
};
