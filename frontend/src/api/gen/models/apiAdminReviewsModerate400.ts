import type { ApiAdminReviewsModerate400Extra } from './apiAdminReviewsModerate400Extra';

/**
 * Validation Exception
 */
export type ApiAdminReviewsModerate400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminReviewsModerate400Extra;
};
