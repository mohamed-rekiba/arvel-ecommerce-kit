import type { ApiProductsIndex400Extra } from './apiProductsIndex400Extra';

/**
 * Validation Exception
 */
export type ApiProductsIndex400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiProductsIndex400Extra;
};
