import type { ApiProductsReviewsIndex400Extra } from './apiProductsReviewsIndex400Extra';

/**
 * Validation Exception
 */
export type ApiProductsReviewsIndex400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiProductsReviewsIndex400Extra;
};
