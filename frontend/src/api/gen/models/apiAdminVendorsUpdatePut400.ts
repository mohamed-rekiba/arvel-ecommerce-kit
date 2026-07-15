import type { ApiAdminVendorsUpdatePut400Extra } from './apiAdminVendorsUpdatePut400Extra';

/**
 * Validation Exception
 */
export type ApiAdminVendorsUpdatePut400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminVendorsUpdatePut400Extra;
};
