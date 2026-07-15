import type { AdminBannerOutTranslations } from './adminBannerOutTranslations';

export interface AdminBannerOut {
  id: number;
  translations: AdminBannerOutTranslations;
  cta_to: string;
  sort: number;
  active: boolean;
  image_url: string | null;
}
