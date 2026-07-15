import type { WebhookInData } from './webhookInData';

export interface WebhookIn {
  id: string;
  type: string;
  data?: WebhookInData;
}
