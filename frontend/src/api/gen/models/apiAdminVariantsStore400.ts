import type { ApiAdminVariantsStore400Extra } from './apiAdminVariantsStore400Extra';

/**
 * Validation Exception
 */
export type ApiAdminVariantsStore400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminVariantsStore400Extra;
};
