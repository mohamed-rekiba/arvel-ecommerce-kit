import type { ApiAdminUsersIndex400Extra } from './apiAdminUsersIndex400Extra';

/**
 * Validation Exception
 */
export type ApiAdminUsersIndex400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminUsersIndex400Extra;
};
