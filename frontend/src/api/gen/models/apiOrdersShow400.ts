import type { ApiOrdersShow400Extra } from './apiOrdersShow400Extra';

/**
 * Validation Exception
 */
export type ApiOrdersShow400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiOrdersShow400Extra;
};
