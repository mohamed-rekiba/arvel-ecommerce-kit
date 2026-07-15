import type { ApiAdminProductsShow400Extra } from './apiAdminProductsShow400Extra';

/**
 * Validation Exception
 */
export type ApiAdminProductsShow400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminProductsShow400Extra;
};
