import type { ApiMediaShow400Extra } from './apiMediaShow400Extra';

/**
 * Validation Exception
 */
export type ApiMediaShow400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiMediaShow400Extra;
};
