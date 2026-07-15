
/**
 * Settlement currencies the shop can charge in (the catalog prices in USD today).
 */
export type Currency = typeof Currency[keyof typeof Currency];


export const Currency = {
  USD: 'USD',
} as const;
