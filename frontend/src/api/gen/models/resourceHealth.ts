
export interface ResourceHealth {
  status: string;
  latency_ms: number;
  detail?: string | null;
}
