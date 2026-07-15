import type { CategoryInTranslations } from './categoryInTranslations';

export interface CategoryIn {
  translations: CategoryInTranslations;
  parent_id?: number | null;
  published?: boolean;
}
