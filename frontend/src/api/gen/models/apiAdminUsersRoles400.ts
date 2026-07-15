import type { ApiAdminUsersRoles400Extra } from './apiAdminUsersRoles400Extra';

/**
 * Validation Exception
 */
export type ApiAdminUsersRoles400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminUsersRoles400Extra;
};
