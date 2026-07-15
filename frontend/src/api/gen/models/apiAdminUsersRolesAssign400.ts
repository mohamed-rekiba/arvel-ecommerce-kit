import type { ApiAdminUsersRolesAssign400Extra } from './apiAdminUsersRolesAssign400Extra';

/**
 * Validation Exception
 */
export type ApiAdminUsersRolesAssign400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminUsersRolesAssign400Extra;
};
