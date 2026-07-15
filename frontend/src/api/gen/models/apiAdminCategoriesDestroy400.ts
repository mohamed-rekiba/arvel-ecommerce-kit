import type { ApiAdminCategoriesDestroy400Extra } from './apiAdminCategoriesDestroy400Extra';

/**
 * Validation Exception
 */
export type ApiAdminCategoriesDestroy400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminCategoriesDestroy400Extra;
};
