import type { GalleryImageOut } from './galleryImageOut';
import type { Translate } from './translate';
import type { VariantOut } from './variantOut';

export interface AdminProductDetailOut {
  id: number;
  slug: string;
  translations: Translate[];
  status: string;
  published: boolean;
  featured: boolean;
  is_visible: boolean;
  price_cents: number;
  category_id: number;
  variants: VariantOut[];
  gallery: GalleryImageOut[];
}
