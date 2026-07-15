
/**
 * Shipping address as submitted — every field optional at the parse layer so the Validator
 * can return field-level 422s (not a shapeless 400).
 */
export interface AddressIn {
  name?: string | null;
  line1?: string | null;
  line2?: string | null;
  city?: string | null;
  postal_code?: string | null;
  country?: string | null;
}
