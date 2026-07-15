import type { ApiMediaConversion400Extra } from './apiMediaConversion400Extra';

/**
 * Validation Exception
 */
export type ApiMediaConversion400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiMediaConversion400Extra;
};
