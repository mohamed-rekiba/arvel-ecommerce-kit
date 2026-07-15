import type { ApiAdminVendorsUpdatePatch400Extra } from './apiAdminVendorsUpdatePatch400Extra';

/**
 * Validation Exception
 */
export type ApiAdminVendorsUpdatePatch400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminVendorsUpdatePatch400Extra;
};
