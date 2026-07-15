import type { ReviewStatus } from './reviewStatus';

export interface ReviewOut {
  id: number;
  rating: number;
  title: string | null;
  body: string;
  status: ReviewStatus;
  author: string | null;
  created_at: string | null;
}
