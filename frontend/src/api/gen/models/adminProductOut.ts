import type { Translate } from './translate';

export interface AdminProductOut {
  id: number;
  slug: string;
  translations: Translate[];
  status: string;
  published: boolean;
  featured: boolean;
  is_visible: boolean;
  price_cents?: number;
  currency?: string;
  image_url?: string | null;
  stock?: number;
  variant_count?: number;
}
