import type { ApiWishlistToggle400Extra } from './apiWishlistToggle400Extra';

/**
 * Validation Exception
 */
export type ApiWishlistToggle400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiWishlistToggle400Extra;
};
