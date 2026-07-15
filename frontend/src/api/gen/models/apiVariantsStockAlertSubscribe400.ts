import type { ApiVariantsStockAlertSubscribe400Extra } from './apiVariantsStockAlertSubscribe400Extra';

/**
 * Validation Exception
 */
export type ApiVariantsStockAlertSubscribe400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiVariantsStockAlertSubscribe400Extra;
};
