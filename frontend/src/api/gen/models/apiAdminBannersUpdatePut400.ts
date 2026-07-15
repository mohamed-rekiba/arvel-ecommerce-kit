import type { ApiAdminBannersUpdatePut400Extra } from './apiAdminBannersUpdatePut400Extra';

/**
 * Validation Exception
 */
export type ApiAdminBannersUpdatePut400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminBannersUpdatePut400Extra;
};
