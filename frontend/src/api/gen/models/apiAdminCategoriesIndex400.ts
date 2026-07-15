import type { ApiAdminCategoriesIndex400Extra } from './apiAdminCategoriesIndex400Extra';

/**
 * Validation Exception
 */
export type ApiAdminCategoriesIndex400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminCategoriesIndex400Extra;
};
