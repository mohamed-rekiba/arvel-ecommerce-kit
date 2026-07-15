import type { ApiAdminBannersUpdatePatch400Extra } from './apiAdminBannersUpdatePatch400Extra';

/**
 * Validation Exception
 */
export type ApiAdminBannersUpdatePatch400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminBannersUpdatePatch400Extra;
};
