import type { ApiProductsShow400Extra } from './apiProductsShow400Extra';

/**
 * Validation Exception
 */
export type ApiProductsShow400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiProductsShow400Extra;
};
