import type { UpdateProductInTranslations } from './updateProductInTranslations';

export interface UpdateProductIn {
  category_id?: number | null;
  price_cents?: number | null;
  status?: string | null;
  published?: boolean | null;
  featured?: boolean | null;
  translations?: UpdateProductInTranslations;
}
