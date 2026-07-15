import type { ReviewOut } from './reviewOut';

export interface ReviewListOut {
  reviews: ReviewOut[];
  mine: ReviewOut | null;
  rating_count: number;
  rating_avg: number | null;
}
