import type { CountryCode } from './countryCode';

export interface SavedAddressOut {
  id: number;
  label: string | null;
  name: string;
  line1: string;
  line2: string | null;
  city: string;
  postal_code: string;
  country: CountryCode;
  phone: string | null;
  is_default: boolean;
}
