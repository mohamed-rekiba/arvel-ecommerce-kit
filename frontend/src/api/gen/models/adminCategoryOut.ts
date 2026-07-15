import type { Translate } from './translate';

export interface AdminCategoryOut {
  id: number;
  slug: string;
  translations: Translate[];
  parent_id?: number | null;
  published?: boolean;
  is_visible?: boolean;
}
