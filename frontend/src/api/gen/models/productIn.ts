import type { ProductInTranslations } from './productInTranslations';

export interface ProductIn {
  category_id: number;
  price_cents: number;
  translations: ProductInTranslations;
}
