import type { ApiAdminProductsCopyDraft400Extra } from './apiAdminProductsCopyDraft400Extra';

/**
 * Validation Exception
 */
export type ApiAdminProductsCopyDraft400 = {
  status_code: number;
  detail: string;
  /** @nullable */
  extra?: ApiAdminProductsCopyDraft400Extra;
};
