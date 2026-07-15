import type { ApiCartItemsRemove400Extra } from './apiCartItemsRemove400Extra';

/**
 * Validation Exception
 */
export type ApiCartItemsRemove400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiCartItemsRemove400Extra;
};
