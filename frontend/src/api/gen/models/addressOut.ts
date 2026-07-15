import type { CountryCode } from './countryCode';

export interface AddressOut {
  name: string;
  line1: string;
  line2: string | null;
  city: string;
  postal_code: string;
  country: CountryCode;
}
