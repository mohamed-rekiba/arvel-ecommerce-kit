import type { CategoryOut } from './categoryOut';
import type { GalleryImageOut } from './galleryImageOut';
import type { ProductDealOut } from './productDealOut';
import type { Translate } from './translate';
import type { VariantOut } from './variantOut';

export interface ProductOut {
  id: number;
  slug: string;
  translation: Translate;
  rating_avg: number | null;
  rating_count: number;
  price_cents: number;
  currency: string;
  status: string;
  featured: boolean;
  created_at: string | null;
  deal: ProductDealOut | null;
  gallery: GalleryImageOut[];
  category?: CategoryOut | null;
  variants?: VariantOut[] | null;
}
