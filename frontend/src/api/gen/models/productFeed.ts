import type { ProductOut } from './productOut';

export interface ProductFeed {
  data: ProductOut[];
  per_page: number;
  next_cursor?: string | null;
  prev_cursor?: string | null;
}
