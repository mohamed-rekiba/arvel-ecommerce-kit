import type { ApiAdminCategoriesUpdatePatch400Extra } from './apiAdminCategoriesUpdatePatch400Extra';

/**
 * Validation Exception
 */
export type ApiAdminCategoriesUpdatePatch400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminCategoriesUpdatePatch400Extra;
};
