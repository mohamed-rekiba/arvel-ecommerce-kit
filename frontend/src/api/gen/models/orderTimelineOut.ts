import type { OrderStatus } from './orderStatus';

export interface OrderTimelineOut {
  status: OrderStatus;
  at: string | null;
}
