import type { ApiCartItemsUpdate400Extra } from './apiCartItemsUpdate400Extra';

/**
 * Validation Exception
 */
export type ApiCartItemsUpdate400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiCartItemsUpdate400Extra;
};
