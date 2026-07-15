
/**
 * Exactly one of ``set`` (absolute) or ``delta`` (shift); ``reason`` lands in the audit log.
 */
export interface StockAdjustIn {
  set?: number | null;
  delta?: number | null;
  reason?: string | null;
}
