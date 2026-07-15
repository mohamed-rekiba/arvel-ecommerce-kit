import type { ApiAdminCategoriesUpdatePut400Extra } from './apiAdminCategoriesUpdatePut400Extra';

/**
 * Validation Exception
 */
export type ApiAdminCategoriesUpdatePut400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminCategoriesUpdatePut400Extra;
};
