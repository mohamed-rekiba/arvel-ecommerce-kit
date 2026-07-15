import type { ApiAdminUsersRolesRevoke400Extra } from './apiAdminUsersRolesRevoke400Extra';

/**
 * Validation Exception
 */
export type ApiAdminUsersRolesRevoke400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminUsersRolesRevoke400Extra;
};
