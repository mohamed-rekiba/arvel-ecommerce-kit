import type { ApiAdminVariantsUpdate400Extra } from './apiAdminVariantsUpdate400Extra';

/**
 * Validation Exception
 */
export type ApiAdminVariantsUpdate400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminVariantsUpdate400Extra;
};
