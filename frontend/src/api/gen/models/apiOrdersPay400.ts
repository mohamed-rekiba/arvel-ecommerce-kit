import type { ApiOrdersPay400Extra } from './apiOrdersPay400Extra';

/**
 * Validation Exception
 */
export type ApiOrdersPay400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiOrdersPay400Extra;
};
