import type { HealthReportResources } from './healthReportResources';

export interface HealthReport {
  status: string;
  healthy: boolean;
  resources: HealthReportResources;
}
