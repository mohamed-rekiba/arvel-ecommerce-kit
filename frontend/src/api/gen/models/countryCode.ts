
/**
 * Countries the shop ships to (ISO 3166-1 alpha-2) — a closed, validated set.
 */
export type CountryCode = typeof CountryCode[keyof typeof CountryCode];


export const CountryCode = {
  CA: 'CA',
  DE: 'DE',
  EG: 'EG',
  FR: 'FR',
  GB: 'GB',
  US: 'US',
} as const;
