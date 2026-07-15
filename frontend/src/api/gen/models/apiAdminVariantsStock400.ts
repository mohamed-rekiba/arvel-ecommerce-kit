import type { ApiAdminVariantsStock400Extra } from './apiAdminVariantsStock400Extra';

/**
 * Validation Exception
 */
export type ApiAdminVariantsStock400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminVariantsStock400Extra;
};
