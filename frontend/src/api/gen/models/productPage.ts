import type { ProductOut } from './productOut';

export interface ProductPage {
  data: ProductOut[];
  current_page: number;
  last_page: number;
  per_page: number;
  total: number;
}
