import type { ApiVariantsStockAlertUnsubscribe400Extra } from './apiVariantsStockAlertUnsubscribe400Extra';

/**
 * Validation Exception
 */
export type ApiVariantsStockAlertUnsubscribe400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiVariantsStockAlertUnsubscribe400Extra;
};
