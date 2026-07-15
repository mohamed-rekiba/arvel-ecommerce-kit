import type { ApiAccountAddressesDestroy400Extra } from './apiAccountAddressesDestroy400Extra';

/**
 * Validation Exception
 */
export type ApiAccountAddressesDestroy400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAccountAddressesDestroy400Extra;
};
