import type { ApiAdminOrdersShow400Extra } from './apiAdminOrdersShow400Extra';

/**
 * Validation Exception
 */
export type ApiAdminOrdersShow400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminOrdersShow400Extra;
};
