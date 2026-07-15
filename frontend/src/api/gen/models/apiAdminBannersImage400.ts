import type { ApiAdminBannersImage400Extra } from './apiAdminBannersImage400Extra';

/**
 * Validation Exception
 */
export type ApiAdminBannersImage400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminBannersImage400Extra;
};
