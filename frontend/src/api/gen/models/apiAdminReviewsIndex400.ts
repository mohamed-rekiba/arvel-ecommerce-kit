import type { ApiAdminReviewsIndex400Extra } from './apiAdminReviewsIndex400Extra';

/**
 * Validation Exception
 */
export type ApiAdminReviewsIndex400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminReviewsIndex400Extra;
};
