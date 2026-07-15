import type { ApiAdminUsersShow400Extra } from './apiAdminUsersShow400Extra';

/**
 * Validation Exception
 */
export type ApiAdminUsersShow400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminUsersShow400Extra;
};
