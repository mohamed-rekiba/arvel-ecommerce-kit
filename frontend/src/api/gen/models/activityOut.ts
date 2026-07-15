import type { ActivityOutProperties } from './activityOutProperties';

export interface ActivityOut {
  id: number;
  description: string;
  event: string | null;
  causer_id: number | null;
  subject_type: string | null;
  subject_id: number | null;
  properties: ActivityOutProperties;
  created_at: string | null;
}
