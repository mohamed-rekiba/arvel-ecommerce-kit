import type { AdminProductOut } from './adminProductOut';

export interface AdminProductPage {
  data: AdminProductOut[];
  current_page: number;
  last_page: number;
  per_page: number;
  total: number;
}
