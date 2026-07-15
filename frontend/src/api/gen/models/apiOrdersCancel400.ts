import type { ApiOrdersCancel400Extra } from './apiOrdersCancel400Extra';

/**
 * Validation Exception
 */
export type ApiOrdersCancel400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiOrdersCancel400Extra;
};
