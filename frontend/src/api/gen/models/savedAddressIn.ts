import type { CountryCode } from './countryCode';

/**
 * Create/update a saved address-book entry (validated at the controller).
 */
export interface SavedAddressIn {
  name: string;
  line1: string;
  city: string;
  postal_code: string;
  country: CountryCode;
  label?: string | null;
  line2?: string | null;
  phone?: string | null;
  is_default?: boolean;
}
