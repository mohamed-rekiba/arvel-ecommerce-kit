import type { ApiAdminBannersDestroy400Extra } from './apiAdminBannersDestroy400Extra';

/**
 * Validation Exception
 */
export type ApiAdminBannersDestroy400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminBannersDestroy400Extra;
};
