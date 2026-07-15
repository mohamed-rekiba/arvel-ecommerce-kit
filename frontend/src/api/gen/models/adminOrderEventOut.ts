import type { AdminOrderEventOutProperties } from './adminOrderEventOutProperties';

export interface AdminOrderEventOut {
  description: string;
  causer_id: number | null;
  properties: AdminOrderEventOutProperties;
  created_at: string | null;
}
