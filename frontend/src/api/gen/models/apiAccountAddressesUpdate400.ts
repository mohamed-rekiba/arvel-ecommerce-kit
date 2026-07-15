import type { ApiAccountAddressesUpdate400Extra } from './apiAccountAddressesUpdate400Extra';

/**
 * Validation Exception
 */
export type ApiAccountAddressesUpdate400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAccountAddressesUpdate400Extra;
};
