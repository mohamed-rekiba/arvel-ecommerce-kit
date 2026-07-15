import type { AdminCategoryOut } from './adminCategoryOut';

export interface AdminCategoryPage {
  data: AdminCategoryOut[];
  current_page: number;
  last_page: number;
  per_page: number;
  total: number;
}
