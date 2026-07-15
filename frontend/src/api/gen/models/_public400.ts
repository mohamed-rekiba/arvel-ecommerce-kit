import type { _Public400Extra } from './_public400Extra';

/**
 * Validation Exception
 */
export type _Public400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: _Public400Extra;
};
