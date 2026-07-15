import type { ApiProductsFeed400Extra } from './apiProductsFeed400Extra';

/**
 * Validation Exception
 */
export type ApiProductsFeed400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiProductsFeed400Extra;
};
