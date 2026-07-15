import type { ApiProductsReviewsStore400Extra } from './apiProductsReviewsStore400Extra';

/**
 * Validation Exception
 */
export type ApiProductsReviewsStore400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiProductsReviewsStore400Extra;
};
