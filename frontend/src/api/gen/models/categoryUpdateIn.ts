import type { CategoryUpdateInTranslations } from './categoryUpdateInTranslations';

export interface CategoryUpdateIn {
  translations?: CategoryUpdateInTranslations;
  parent_id?: number | null;
  published?: boolean | null;
}
