import type { ApiAdminVariantsIndex400Extra } from './apiAdminVariantsIndex400Extra';

/**
 * Validation Exception
 */
export type ApiAdminVariantsIndex400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminVariantsIndex400Extra;
};
